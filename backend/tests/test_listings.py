"""
Listings Tests - Theory of Mind:
- Test rate limiting = enforce scarcity psychology
- Test filtering = show power user features
- Test upgrade prompts = conversion opportunities
"""

import pytest
from fastapi import status
from datetime import date


class TestGetListings:
    """Test listing retrieval"""

    def test_get_listings_requires_auth(self, client, test_listings):
        """Should require authentication"""
        response = client.get("/listings")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_listings_success(self, client, auth_headers, test_listings):
        """Should return listings with pagination"""
        response = client.get("/listings", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "listings" in data
        assert "total" in data
        assert "accessible" in data
        assert data["total"] == 15  # Total listings created
        assert len(data["listings"]) <= 15

    def test_get_listings_shows_total_count(self, client, auth_headers, test_listings):
        """
        Theory of Mind: Show total count = user knows what they're missing
        Creates FOMO for premium features
        """
        response = client.get("/listings", headers=auth_headers)

        data = response.json()
        assert data["total"] >= data["accessible"]
        # Free tier can only access 10
        assert data["accessible"] <= 10

    def test_get_listings_filter_by_price(self, client, auth_headers, test_listings):
        """Should filter by price range"""
        response = client.get(
            "/listings?min_price=1900&max_price=2100",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for listing in data["listings"]:
            assert 1900 <= listing["price"] <= 2100

    def test_get_listings_filter_by_bedrooms(self, client, auth_headers, test_listings):
        """Should filter by bedroom count"""
        response = client.get(
            "/listings?min_beds=2&max_beds=2",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for listing in data["listings"]:
            assert listing["bedrooms"] == 2

    def test_get_listings_filter_by_zip(self, client, auth_headers, test_listings):
        """Should filter by zip code"""
        response = client.get(
            "/listings?zip_code=37206",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for listing in data["listings"]:
            assert listing["zip_code"] == "37206"

    def test_get_listings_sorting(self, client, auth_headers, test_listings):
        """Should sort by specified field"""
        # Sort by price ascending
        response = client.get(
            "/listings?sort_by=price&sort_order=asc",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        prices = [l["price"] for l in data["listings"]]
        assert prices == sorted(prices)

    def test_get_listings_pagination(self, client, auth_headers, test_listings):
        """Should paginate results"""
        # Page 1
        response1 = client.get(
            "/listings?page=1&page_size=5",
            headers=auth_headers
        )
        data1 = response1.json()
        assert len(data1["listings"]) == 5

        # Page 2
        response2 = client.get(
            "/listings?page=2&page_size=5",
            headers=auth_headers
        )
        data2 = response2.json()
        assert len(data2["listings"]) == 5

        # Should be different listings
        ids1 = [l["id"] for l in data1["listings"]]
        ids2 = [l["id"] for l in data2["listings"]]
        assert set(ids1).isdisjoint(set(ids2))


class TestGetSingleListing:
    """Test single listing retrieval"""

    def test_get_listing_success(self, client, auth_headers, test_listings, db):
        """Should return single listing and track view"""
        listing_id = test_listings[0].id

        response = client.get(f"/listings/{listing_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == listing_id

        # Should track view
        from app import models
        views = db.query(models.UserActivity).filter(
            models.UserActivity.listing_id == listing_id
        ).count()
        assert views == 1

    def test_get_listing_not_found(self, client, auth_headers):
        """Should return 404 for non-existent listing"""
        response = client.get("/listings/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_listing_enforces_rate_limit(self, client, auth_headers, test_listings, test_user, db):
        """
        Theory of Mind: Rate limit creates scarcity
        Forces upgrade decision
        """
        from app import models

        # Use up all views
        today = date.today().strftime("%Y%m%d")
        for i in range(10):
            view = models.UserActivity(
                user_id=test_user.id,
                listing_id=1,
                view_date=today,
                action="view"
            )
            db.add(view)
        db.commit()

        # Next view should be blocked
        response = client.get(f"/listings/{test_listings[0].id}", headers=auth_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "limit" in response.json()["detail"].lower()

    def test_get_listing_premium_no_limit(self, client, auth_headers_premium, test_listings, test_user_premium, db):
        """Premium users should have unlimited views"""
        from app import models

        # View 20 listings (more than free limit)
        for i in range(20):
            if i < len(test_listings):
                response = client.get(
                    f"/listings/{test_listings[i].id}",
                    headers=auth_headers_premium
                )
                # All should succeed
                assert response.status_code == status.HTTP_200_OK


class TestMarketStats:
    """Test market statistics"""

    def test_get_market_stats(self, client, auth_headers, test_listings):
        """Should return market statistics"""
        response = client.get("/listings/stats/market", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_listings" in data
        assert "avg_price" in data
        assert "min_price" in data
        assert "max_price" in data
        assert data["total_listings"] == 15

    def test_get_market_stats_by_zip(self, client, auth_headers, test_listings):
        """Should filter stats by zip code"""
        response = client.get(
            "/listings/stats/market?zip_code=37206",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_listings"] > 0

    def test_get_market_stats_top_deals_premium_only(self, client, auth_headers, auth_headers_premium, test_listings):
        """
        Theory of Mind: Top deals for premium = shows upgrade value
        Free users see they're missing out
        """
        # Free user
        response_free = client.get("/listings/stats/market", headers=auth_headers)
        data_free = response_free.json()
        assert data_free["top_deals"] == []
        assert data_free["upgrade_message"] is not None

        # Premium user
        response_premium = client.get("/listings/stats/market", headers=auth_headers_premium)
        data_premium = response_premium.json()
        assert len(data_premium["top_deals"]) > 0
        assert data_premium["upgrade_message"] is None


class TestSavedSearches:
    """Test saved search functionality"""

    def test_create_saved_search(self, client, auth_headers, test_user, db):
        """Should create saved search"""
        response = client.post(
            "/listings/saved-searches",
            headers=auth_headers,
            json={
                "name": "East Nashville 2BR",
                "filters": {
                    "zip_code": "37206",
                    "min_beds": 2,
                    "max_price": 2000
                },
                "alert_frequency": "daily"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "East Nashville 2BR"
        assert data["filters"]["zip_code"] == "37206"

    def test_create_saved_search_free_tier_limit(self, client, auth_headers, test_user, db):
        """
        Theory of Mind: Free tier gets taste of feature
        Then hits limit = upgrade prompt
        """
        from app import models

        # Create first search (should succeed)
        response1 = client.post(
            "/listings/saved-searches",
            headers=auth_headers,
            json={
                "name": "Search 1",
                "filters": {},
                "alert_frequency": "never"
            }
        )
        assert response1.status_code == status.HTTP_200_OK

        # Create second search (should fail)
        response2 = client.post(
            "/listings/saved-searches",
            headers=auth_headers,
            json={
                "name": "Search 2",
                "filters": {},
                "alert_frequency": "never"
            }
        )
        assert response2.status_code == status.HTTP_403_FORBIDDEN
        assert "upgrade" in response2.json()["detail"].lower()

    def test_get_saved_searches(self, client, auth_headers, test_user, db):
        """Should return user's saved searches"""
        from app import models

        # Create a search
        search = models.SavedSearch(
            user_id=test_user.id,
            name="My Search",
            filters='{"zip_code": "37206"}',
            alert_frequency="daily"
        )
        db.add(search)
        db.commit()

        response = client.get("/listings/saved-searches", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "My Search"

    def test_delete_saved_search(self, client, auth_headers, test_user, db):
        """Should delete saved search"""
        from app import models

        # Create a search
        search = models.SavedSearch(
            user_id=test_user.id,
            name="To Delete",
            filters='{}',
            alert_frequency="never"
        )
        db.add(search)
        db.commit()
        db.refresh(search)

        response = client.delete(
            f"/listings/saved-searches/{search.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Should be gone
        deleted = db.query(models.SavedSearch).filter(
            models.SavedSearch.id == search.id
        ).first()
        assert deleted is None

    def test_delete_saved_search_not_found(self, client, auth_headers):
        """Should return 404 for non-existent search"""
        response = client.delete("/listings/saved-searches/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTheoryOfMind:
    """Test psychological conversion triggers"""

    def test_upgrade_message_when_limit_exceeded(self, client, auth_headers, test_listings, test_user, db):
        """
        Theory of Mind: Show upgrade message at friction point
        Clear CTA when user hits limit
        """
        from app import models

        # Use up views
        today = date.today().strftime("%Y%m%d")
        for i in range(10):
            view = models.UserActivity(
                user_id=test_user.id,
                listing_id=1,
                view_date=today,
                action="view"
            )
            db.add(view)
        db.commit()

        # Try to view another
        response = client.get(f"/listings/{test_listings[0].id}", headers=auth_headers)

        # Should get clear upgrade message
        assert "upgrade" in response.json()["detail"].lower()

    def test_total_vs_accessible_creates_fomo(self, client, auth_headers, test_listings):
        """
        Theory of Mind: Show total > accessible = FOMO
        User sees they're missing listings
        """
        response = client.get("/listings", headers=auth_headers)

        data = response.json()
        # 15 total listings but free user can only access 10
        assert data["total"] == 15
        assert data["accessible"] == 10
        # Gap creates desire to upgrade
        assert data["total"] > data["accessible"]
