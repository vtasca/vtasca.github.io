from scour.scour import scourString, generateDefaultOptions
import os

def optimize_svg(input_file, output_file=None):
    """
    Optimize an SVG file using Scour.
    
    Args:
        input_file (str): Path to the input SVG file
        output_file (str, optional): Path to save the optimized SVG. If None, will overwrite input file.
    """
    # Read the input SVG file
    with open(input_file, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    
    # Get default options
    options = generateDefaultOptions()
    
    # Customize optimization options
    options.strip_ids = True  # Remove unused IDs
    options.simple_colors = True  # Convert colors to #RRGGBB format
    options.strip_comments = True  # Remove comments
    options.strip_xml_space_attribute = True  # Remove xml:space attributes
    options.group_create = True  # Create groups for elements with common attributes
    options.group_collapse = True  # Collapse groups with common attributes
    options.digits = 3  # Number of significant digits to keep in numbers
    options.cdigits = 3  # Number of significant digits to keep in control points
    
    # Optimize the SVG
    optimized_svg = scourString(svg_content, options)
    
    # Determine output file path
    if output_file is None:
        output_file = input_file
    
    # Save the optimized SVG
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(optimized_svg)
    
    # Print some statistics
    original_size = os.path.getsize(input_file)
    optimized_size = os.path.getsize(output_file)
    savings = original_size - optimized_size
    savings_percent = (savings / original_size) * 100
    
    print(f"Original size: {original_size} bytes")
    print(f"Optimized size: {optimized_size} bytes")
    print(f"Savings: {savings} bytes ({savings_percent:.1f}%)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: uv run optimize_svg.py <svg_file> <output_file> (optional)")
        print("Example: uv run optimize_svg.py icon.svg")
        print("or: uv run optimize_svg.py icon.svg icon_optimized.svg")
        sys.exit(1)
        
    svg_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        optimize_svg(svg_file, output_file)
    except Exception as e:
        print(f"Error optimizing SVG file: {e}")
        sys.exit(1)