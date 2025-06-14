"""
Strategy Builder routes
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def builder_page():
    """Strategy builder page - placeholder"""
    return {"message": "Strategy builder coming soon!"}