"""
Avatar utility functions for handling user avatars in the Nest application.

This module provides functions to load, process, and manage user avatars from various sources
including RepairDesk API, local files, and generated avatars.
"""

import os
import hashlib
import logging
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import tkinter as tk
from typing import Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Avatar cache to avoid reloading the same image multiple times
_avatar_cache = {}

def get_avatar_url(user_data: dict, size: str = 'small') -> Optional[str]:
    """
    Get the avatar URL for a user from the user data.
    
    Args:
        user_data: Dictionary containing user data
        size: Desired size of the avatar ('small', 'medium', 'large')
        
    Returns:
        str: URL of the avatar image or None if not available
    """
    try:
        # Try to get avatar from user data
        if 'image' in user_data and user_data['image']:
            # Handle RepairDesk avatar URL format
            if 'repairdesk' in user_data['image'].lower() or 'cloudfront' in user_data['image'].lower():
                # Ensure proper URL encoding for spaces
                return user_data['image'].replace(' ', '%20')
            return user_data['image']
            
        # Fallback to ID-based URL for RepairDesk
        if 'id' in user_data and user_data['id']:
            user_id = str(user_data['id']).split('.')[-1]  # Handle decimal IDs
            return f"https://dghyt15qon7us.cloudfront.net/images/productTheme/User/{size}/{user_id}.jpg"
            
    except Exception as e:
        logger.error(f"Error getting avatar URL: {str(e)}")
        
    return None

def get_initial_avatar(name: str, size: int = 100, bg_color: str = "#2e7d32") -> Image.Image:
    """
    Generate an avatar with the user's initials.
    
    Args:
        name: User's name to generate initials from
        size: Size of the avatar in pixels
        bg_color: Background color in hex format
        
    Returns:
        PIL.Image: Generated avatar image
    """
    # Create a new image with the specified background color
    image = Image.new('RGBA', (size, size), bg_color)
    draw = ImageDraw.Draw(image)
    
    try:
        # Try to load a nice font
        font_size = int(size * 0.5)
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        # Fallback to default font if Arial is not available
        font = ImageFont.load_default()
    
    # Get initials (first letter of first and last name)
    parts = name.strip().split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    else:
        initials = name[:2].upper() if name else "??"
    
    # Calculate text position
    text_bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    position = ((size - text_width) // 2, (size - text_height) // 2 - 5)
    
    # Draw the text
    draw.text(position, initials, font=font, fill="#ffffff")
    
    return image

def load_avatar_image(url: str, size: Tuple[int, int] = (100, 100)) -> Optional[Image.Image]:
    """
    Load an avatar image from a URL and resize it.
    
    Args:
        url: URL of the image
        size: Desired size as (width, height)
        
    Returns:
        PIL.Image: Resized image or None if loading fails
    """
    cache_key = f"{url}_{size[0]}x{size[1]}"
    if cache_key in _avatar_cache:
        return _avatar_cache[cache_key]
    
    try:
        # Handle local file paths
        if url.startswith('file://'):
            path = url[7:]
            img = Image.open(path)
        # Handle remote URLs
        elif url.startswith(('http://', 'https://')):
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
        else:
            # Assume it's a local file path
            img = Image.open(url)
        
        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        # Resize the image
        img.thumbnail(size, Image.LANCZOS)
        
        # Create a circular mask for the image
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)
        
        # Apply the mask
        result = Image.new('RGBA', size, (0, 0, 0, 0))
        result.paste(img, (0, 0), mask)
        
        # Cache the result
        _avatar_cache[cache_key] = result
        return result
        
    except Exception as e:
        logger.error(f"Error loading avatar from {url}: {str(e)}")
        return None

def get_avatar_image(user_data: dict, size: Tuple[int, int] = (100, 100)) -> Image.Image:
    """
    Get an avatar image for the user, with fallbacks.
    
    Args:
        user_data: Dictionary containing user data
        size: Desired size as (width, height)
        
    Returns:
        PIL.Image: Avatar image
    """
    # Try to get avatar from URL first
    avatar_url = get_avatar_url(user_data)
    if avatar_url:
        img = load_avatar_image(avatar_url, size)
        if img:
            return img
    
    # Fall back to generated initials avatar
    name = user_data.get('name', '') or user_data.get('username', 'User')
    return get_initial_avatar(name, max(size))

def get_avatar_photoimage(user_data: dict, size: Tuple[int, int] = (100, 100)) -> Optional[tk.PhotoImage]:
    """
    Get a Tkinter PhotoImage for the user's avatar.
    
    Args:
        user_data: Dictionary containing user data
        size: Desired size as (width, height)
        
    Returns:
        tk.PhotoImage: Avatar as a PhotoImage or None if loading fails
    """
    try:
        img = get_avatar_image(user_data, size)
        if img:
            # Convert PIL Image to PhotoImage
            from PIL import ImageTk
            return ImageTk.PhotoImage(img)
    except Exception as e:
        logger.error(f"Error creating PhotoImage: {str(e)}")
    return None

def get_avatar_for_user(user_data: dict = None, size: Tuple[int, int] = (100, 100), user_id: str = None) -> Optional[Image.Image]:
    """
    Get an avatar image for the user (compatibility function).
    
    Args:
        user_data: Dictionary containing user data
        size: Desired size as (width, height)
        user_id: User ID (alternative to user_data)
        
    Returns:
        PIL.Image: Avatar image or None if loading fails
    """
    try:
        if user_data is None and user_id is not None:
            # Create a minimal user data dict with just the ID
            user_data = {'id': user_id}
        return get_avatar_image(user_data, size)
    except Exception as e:
        logger.error(f"Error in get_avatar_for_user: {str(e)}")
        return None
