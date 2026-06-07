from fastapi import APIRouter

from api.app.services.property_search import search_properties

router = APIRouter(prefix="/properties")


@router.get("/search")
def property_search(location: str = "", min_bedrooms: int = 0):
    """Return property listings matching the user's filters."""
    return {
        "results": search_properties(location=location, min_bedrooms=min_bedrooms)
    }
