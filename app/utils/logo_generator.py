"""Logo generator for MGG_SYS"""
from PIL import Image, ImageDraw, ImageFont
import os
from app.utils.paths import get_project_root


class LogoGenerator:
    """Generates system logo programmatically"""

    @staticmethod
    def generate_logo(output_path: str = None, size: tuple = (200, 200)) -> str:
        """
        Generate MGG system logo.

        Args:
            output_path: Path to save the logo (optional)
            size: Logo dimensions (width, height)

        Returns:
            str: Path to the generated logo
        """
        if output_path is None:
            project_root = get_project_root()
            output_path = os.path.join(project_root, 'app', 'static', 'assets', 'logos', 'mgg_logo.png')

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Create image with gradient background
        img = Image.new('RGB', size, color='white')
        draw = ImageDraw.Draw(img)

        # Draw gradient background (purple gradient)
        for i in range(size[1]):
            # Gradient from #667eea to #764ba2
            r = int(102 + (118 - 102) * i / size[1])
            g = int(126 + (75 - 126) * i / size[1])
            b = int(234 + (162 - 234) * i / size[1])
            draw.rectangle([(0, i), (size[0], i + 1)], fill=(r, g, b))

        # Draw circle background for letters
        center_x, center_y = size[0] // 2, size[1] // 2
        circle_radius = min(size) // 2 - 20
        draw.ellipse(
            [center_x - circle_radius, center_y - circle_radius,
             center_x + circle_radius, center_y + circle_radius],
            fill='white',
            outline='#667eea',
            width=4
        )

        # Try to use a nice font, fall back to default if not available
        try:
            # Try to load a system font
            font_size = int(circle_radius * 0.8)
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()

        # Draw "MGG" text in center
        text = "MGG"

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text
        text_x = center_x - text_width // 2
        text_y = center_y - text_height // 2 - 10

        # Draw text with shadow for depth
        shadow_offset = 2
        draw.text((text_x + shadow_offset, text_y + shadow_offset), text, font=font, fill='#cccccc')
        draw.text((text_x, text_y), text, font=font, fill='#667eea')

        # Draw subtitle
        try:
            subtitle_font_size = int(font_size * 0.25)
            subtitle_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', subtitle_font_size)
        except:
            subtitle_font = ImageFont.load_default()

        subtitle = "仿真系统"
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = center_x - subtitle_width // 2
        subtitle_y = center_y + text_height // 2 + 15

        draw.text((subtitle_x, subtitle_y), subtitle, font=subtitle_font, fill='white')

        # Save the image
        img.save(output_path, 'PNG', quality=95)

        return output_path

    @staticmethod
    def generate_favicon(logo_path: str = None) -> str:
        """
        Generate favicon from logo.

        Args:
            logo_path: Path to the source logo

        Returns:
            str: Path to the generated favicon
        """
        if logo_path is None:
            project_root = get_project_root()
            logo_path = os.path.join(project_root, 'app', 'static', 'assets', 'logos', 'mgg_logo.png')

        favicon_path = os.path.join(os.path.dirname(logo_path), 'favicon.ico')

        # Load and resize logo
        img = Image.open(logo_path)
        img = img.resize((32, 32), Image.Resampling.LANCZOS)

        # Save as ICO
        img.save(favicon_path, format='ICO')

        return favicon_path

    @staticmethod
    def ensure_logos_exist():
        """
        Ensure logo files exist, generate if missing.

        Returns:
            dict: Paths to logo files
        """
        project_root = get_project_root()
        logo_path = os.path.join(project_root, 'app', 'static', 'assets', 'logos', 'mgg_logo.png')
        favicon_path = os.path.join(project_root, 'app', 'static', 'assets', 'logos', 'favicon.ico')

        paths = {
            'logo': logo_path,
            'favicon': favicon_path
        }

        # Generate logo if it doesn't exist
        if not os.path.exists(logo_path):
            LogoGenerator.generate_logo(logo_path)

        # Generate favicon if it doesn't exist
        if not os.path.exists(favicon_path):
            LogoGenerator.generate_favicon(logo_path)

        return paths
