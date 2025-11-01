"""
Listings Routes - Theory of Mind:
- Show total count = user knows what they're missing
- Enforce rate limits = creates upgrade pressure
- Clear upgrade messaging = friction converts to revenue
- Rich filtering = power users see value
"""

from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from ..database import get_db
from ..config import get_settings
from .. import models, schemas, auth

router = APIRouter(prefix="/listings", tags=["Listings"])
settings = get_settings()


@router.get("", response_model=schemas.ListingListResponse)
async def get_listings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
    # Filters
    zip_code: Optional[str] = Query(None, description="Filter by zip code"),
    min_price: Optional[int] = Query(None, description="Minimum rent price"),
    max_price: Optional[int] = Query(None, description="Maximum rent price"),
    min_beds: Optional[int] = Query(None, description="Minimum bedrooms"),
    max_beds: Optional[int] = Query(None, description="Maximum bedrooms"),
    min_baths: Optional[float] = Query(None, description="Minimum bathrooms"),
    min_sqft: Optional[int] = Query(None, description="Minimum square feet"),
    max_sqft: Optional[int] = Query(None, description="Maximum square feet"),
    # Sorting & Pagination
    sort_by: Optional[str] = Query("date_posted", description="Sort field (price, date_posted, deal_score)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Get listings with filters and pagination
    Theory of Mind: User sees total but can only access their tier limit
    """
    # Check rate limit
    today = date.today().strftime("%Y%m%d")
    rate_limit_info = auth.check_rate_limit(db, current_user, today)

    # Build query with filters
    query = db.query(models.Listing)

    if zip_code:
        query = query.filter(models.Listing.zip_code == zip_code)
    if min_price:
        query = query.filter(models.Listing.price >= min_price)
    if max_price:
        query = query.filter(models.Listing.price <= max_price)
    if min_beds:
        query = query.filter(models.Listing.bedrooms >= min_beds)
    if max_beds:
        query = query.filter(models.Listing.bedrooms <= max_beds)
    if min_baths:
        query = query.filter(models.Listing.bathrooms >= min_baths)
    if min_sqft:
        query = query.filter(models.Listing.sqft >= min_sqft)
    if max_sqft:
        query = query.filter(models.Listing.sqft <= max_sqft)

    # Get total count (shows user what exists)
    total = query.count()

    # Apply sorting
    sort_field = {
        "price": models.Listing.price,
        "date_posted": models.Listing.ingestion_date,
        "deal_score": models.Listing.deal_score,
    }.get(sort_by, models.Listing.ingestion_date)

    if sort_order == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    listings = query.all()

    # Theory of Mind: Free tier sees total (creates FOMO)
    # but response will be filtered by frontend based on rate limit
    return schemas.ListingListResponse(
        listings=[schemas.ListingResponse.model_validate(listing) for listing in listings],
        total=total,
        accessible=rate_limit_info["remaining"],
        page=page,
        page_size=page_size,
        upgrade_message=rate_limit_info.get("upgrade_message")
    )


@router.get("/{listing_id}", response_model=schemas.ListingResponse)
async def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Get single listing detail
    Theory of Mind: Track this view for rate limiting
    """
    # Check rate limit
    today = date.today().strftime("%Y%m%d")
    rate_limit_info = auth.check_rate_limit(db, current_user, today)

    if rate_limit_info["exceeded"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=rate_limit_info.get("upgrade_message", "Daily view limit exceeded")
        )

    # Get listing
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )

    # Track view
    view = models.UserActivity(
        user_id=current_user.id,
        listing_id=listing_id,
        view_date=today,
        action="view"
    )
    db.add(view)
    db.commit()

    return schemas.ListingResponse.model_validate(listing)


@router.get("/stats/market", response_model=schemas.MarketStats)
async def get_market_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
    zip_code: Optional[str] = Query(None, description="Filter stats by zip code"),
):
    """
    Get market statistics
    Theory of Mind: Investor Pro feature - shows value of upgrade
    """
    # Build query
    query = db.query(models.Listing)
    if zip_code:
        query = query.filter(models.Listing.zip_code == zip_code)

    # Calculate stats
    stats = db.query(
        func.avg(models.Listing.price).label("avg_price"),
        func.min(models.Listing.price).label("min_price"),
        func.max(models.Listing.price).label("max_price"),
        func.avg(models.Listing.deal_score).label("avg_deal_score"),
        func.count(models.Listing.id).label("total_listings")
    ).filter(
        models.Listing.zip_code == zip_code if zip_code else True
    ).first()

    # Get top deals (only for paid tiers)
    top_deals = []
    if current_user.tier != "free":
        top_deals_query = db.query(models.Listing).filter(
            models.Listing.zip_code == zip_code if zip_code else True
        ).order_by(models.Listing.deal_score.desc()).limit(5)
        top_deals = [schemas.ListingResponse.model_validate(l) for l in top_deals_query.all()]

    return schemas.MarketStats(
        avg_price=float(stats.avg_price) if stats.avg_price else 0,
        min_price=stats.min_price or 0,
        max_price=stats.max_price or 0,
        avg_deal_score=float(stats.avg_deal_score) if stats.avg_deal_score else 0,
        total_listings=stats.total_listings or 0,
        top_deals=top_deals,
        upgrade_message="Upgrade to see top deals" if current_user.tier == "free" else None
    )


@router.post("/saved-searches", response_model=schemas.SavedSearchResponse)
async def create_saved_search(
    search: schemas.SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Save search criteria (Premium feature)
    Theory of Mind: Free tier can try, but hits limit quickly
    """
    # Check if free tier
    if current_user.tier == "free":
        # Free tier gets 1 saved search
        existing_count = db.query(models.SavedSearch).filter(
            models.SavedSearch.user_id == current_user.id
        ).count()

        if existing_count >= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Free tier limited to 1 saved search. Upgrade for unlimited searches."
            )

    # Create saved search
    db_search = models.SavedSearch(
        user_id=current_user.id,
        name=search.name,
        filters=search.filters,
        alert_frequency=search.alert_frequency
    )
    db.add(db_search)
    db.commit()
    db.refresh(db_search)

    return schemas.SavedSearchResponse.model_validate(db_search)


@router.get("/saved-searches", response_model=list[schemas.SavedSearchResponse])
async def get_saved_searches(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """Get user's saved searches"""
    searches = db.query(models.SavedSearch).filter(
        models.SavedSearch.user_id == current_user.id
    ).all()

    return [schemas.SavedSearchResponse.model_validate(s) for s in searches]


@router.delete("/saved-searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """Delete saved search"""
    search = db.query(models.SavedSearch).filter(
        models.SavedSearch.id == search_id,
        models.SavedSearch.user_id == current_user.id
    ).first()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )

    db.delete(search)
    db.commit()

    return None
