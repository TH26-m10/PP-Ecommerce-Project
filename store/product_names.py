import random

BRANDS = [
    'Samsung', 'Apple', 'Sony', 'Logitech', 'Dell', 'HP', 'Anker', 'JBL',
    'Canon', 'Nike', 'Adidas', 'Lenovo', 'Asus', 'Microsoft', 'Bose',
    'Philips', 'KitchenAid', 'Dyson', 'Garmin', 'Razer', 'Corsair',
    'Under Armour', 'Levi\'s', 'North Face', 'Patagonia', 'IKEA',
]

PRODUCT_TYPES = [
    'Wireless Earbuds', 'Bluetooth Speaker', 'USB-C Hub 7-in-1',
    'Laptop Sleeve 15"', 'Ergonomic Wireless Mouse', 'Mechanical Keyboard RGB',
    '27" 4K Monitor', 'HD Webcam 1080p', 'Portable SSD 1TB',
    'Fast Phone Charger 65W', 'Running Shoes', 'Cotton Crew T-Shirt',
    'Slim Fit Jeans', 'Waterproof Winter Jacket', 'Drip Coffee Maker',
    'High-Speed Blender', 'HEPA Air Purifier', 'Robot Vacuum Cleaner',
    'Smart Watch Series', 'Fitness Tracker Band', 'Noise Cancelling Headphones',
    'Tablet Stand Adjustable', 'USB-C to HDMI Cable', 'Wireless Charging Pad',
    'Gaming Headset 7.1', 'Office Desk Chair', 'LED Desk Lamp',
    'Travel Backpack 40L', 'Insulated Water Bottle', 'Yoga Mat Premium',
    'Cast Iron Skillet 12"', 'Non-Stick Cookware Set', 'Electric Kettle 1.7L',
    'Toaster Oven 4-Slice', 'Memory Foam Pillow', 'Cotton Bed Sheets Set',
    'Bluetooth Car Adapter', 'Dash Cam Front/Rear', 'Tire Inflator Portable',
    'Camping Tent 4-Person', 'Sleeping Bag Lightweight', 'Hiking Boots',
    'Polarized Sunglasses', 'Leather Wallet', 'Canvas Sneakers',
    'Graphic Hoodie', 'Sports Leggings', 'Resistance Bands Set',
    'Adjustable Dumbbells', 'Foam Roller', 'Protein Shaker Bottle',
]


def realistic_product_names(count=300):
    """Generate unique realistic e-commerce product names."""
    names = set()
    variants = ['Pro', 'Plus', 'Max', 'Lite', 'Elite', '2024', 'V2', '']

    while len(names) < count:
        brand = random.choice(BRANDS)
        product = random.choice(PRODUCT_TYPES)
        variant = random.choice(variants)
        if variant:
            name = f'{brand} {product} {variant}'.strip()
        else:
            name = f'{brand} {product}'
        names.add(name)

    return list(names)
