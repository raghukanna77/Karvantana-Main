"""Seed DEMO data for KARVANTANA.

Everything created here is clearly-labeled, fictional demo data (is_demo=True)
for hackathon presentation and local development. Never run against production.

Usage:  python3 seed_demo.py
"""

from __future__ import annotations

import io
import math
import random

from decimal import Decimal
from datetime import datetime, timedelta, timezone

from app.core.database import Base, SessionLocal, engine
from app.models import new_uuid
from app.models.catalog import Category, CraftType, Language, Material
from app.models.commerce import (
    BulkRequest, CustomRequest, Order, OrderItem, OrderStatus, OrderStatusHistory,
    Payment, Quote, QuoteStatus,
)
from app.models.engagement import ArtisanReputation, Follow, Review, SavedArtisan
from app.models.product import Product, ProductImage, ProductLifecycle
from app.models.profile import ArtisanProfile, BuyerProfile, BusinessProfile, Cluster, ClusterMember
from app.models.user import User
from app.security.passwords import hash_password
import app.models  # register all

random.seed(42)

DEMO_MARK = "[DEMO]"


def _swatch(name: str, base: tuple[int, int, int], accent: tuple[int, int, int], size: int = 640) -> bytes:
    """Generate a simple product-photo placeholder image (no stock photos used)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (size, size), (244, 242, 238))
    draw = ImageDraw.Draw(img)
    w = size // 2
    x0, y0 = (size - w) // 2, (size - w) // 2
    draw.rounded_rectangle((x0, y0, x0 + w, y0 + w), radius=48, fill=base)
    for i in range(6):
        offset = 24 + i * (w - 48) // 6
        draw.line((x0 + offset, y0 + 16, x0 + offset, y0 + w - 16), fill=accent, width=3)
    draw.ellipse((x0 + w - 64, y0 + 16, x0 + w - 24, y0 + 56), fill=accent)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _save(data: bytes, name: str) -> str:
    import os

    from app.core.config import get_settings

    media = get_settings().MEDIA_DIR
    os.makedirs(media, exist_ok=True)
    path = os.path.join(media, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return f"/media/{name}"


ARTISANS = [
    {"name": "Priya's Handloom Studio", "person": "Priya", "craft": "Handloom Weaving",
     "state": "Tamil Nadu", "district": "Madurai", "village": "Kanadipatti",
     "story": "Priya learned to weave at her grandmother's loom in Kanadipatti. Today her studio keeps the tradition alive with natural-dye cotton sarees.",
     "years": 12, "org": "INDIVIDUAL", "lang": "ta,en", "color": ((196, 90, 74), (122, 60, 52))},
    {"name": "Bamboo Craft Collective", "person": "Arun", "craft": "Bamboo Weaving",
     "state": "Assam", "district": "Kamrup", "village": "Hajo",
     "story": "Arun leads a group of 14 bamboo weavers near Hajo, crafting storage baskets and lamps from sustainably harvested bamboo.",
     "years": 9, "org": "COOPERATIVE", "lang": "as,en", "color": ((86, 124, 66), (56, 86, 44))},
    {"name": "Rangoli Terracotta Works", "person": "Meena", "craft": "Terracotta Pottery",
     "state": "Rajasthan", "district": "Jaipur", "village": "Sanganer",
     "story": "Meena's family has shaped Rajasthani clay for three generations — cookware, planters and decor fired in traditional kilns.",
     "years": 15, "org": "SHG", "lang": "hi,en", "color": ((178, 118, 82), (120, 76, 50))},
    {"name": "Nilgiri Coir Crafts", "person": "Lakshmi", "craft": "Coir Craft",
     "state": "Kerala", "district": "Alappuzha", "village": "Punnamada",
     "story": "Lakshmi's SHG turns coconut coir from the Punnamada backwaters into mats, baskets and planters.",
     "years": 7, "org": "SHG", "lang": "ml,en", "color": ((150, 128, 84), (104, 88, 56))},
    {"name": "Chinar Wood Carvings", "person": "Bashir", "craft": "Wood Carving",
     "state": "Kashmir", "district": "Srinagar", "village": "Nowshera",
     "story": "Bashir carves walnut wood in the Srinagar tradition — bowls, boxes and screens with chinar-leaf motifs.",
     "years": 20, "org": "INDIVIDUAL", "lang": "ks,en", "color": ((122, 90, 60), (84, 60, 40))},
    {"name": "Dhokra Brass Collective", "person": "Sunita", "craft": "Dhokra Brass Casting",
     "state": "Odisha", "district": "Mayurbhanj", "village": "Kuliana",
     "story": "Sunita's collective practices dhokra lost-wax casting, casting bells, figures and lamps in brass.",
     "years": 11, "org": "COOPERATIVE", "lang": "or,en", "color": ((168, 132, 66), (118, 92, 44))},
]

PRODUCTS = [
    # (artisan_idx, title, material, technique, price, days, mode, stock, cat, story_line, keywords)
    (0, "Madurai Handwoven Cotton Saree — Natural Dye", "Cotton", "Handloom", 1250, 4, "MADE_TO_ORDER", 0,
     "Sarees", "Woven on a pit loom with azo-free natural dyes.", "handwoven saree, cotton, natural dye, tamil nadu, handloom"),
    (0, "Kanchi Cotton Saree — Indigo Checks", "Cotton", "Handloom", 1450, 5, "MADE_TO_ORDER", 0,
     "Sarees", "Classic indigo checks with a contrasting temple border.", "handwoven saree, indigo, checks, handloom"),
    (1, "Bamboo Storage Basket — Medium", "Bamboo", "Handwoven", 420, 2, "STOCK", 24,
     "Storage", "Tight-weave basket for kitchen storage; holds up to 5 kg.", "bamboo basket, storage, eco friendly, handmade"),
    (1, "Bamboo Fruit Basket with Handles", "Bamboo", "Handwoven", 520, 2, "STOCK", 18,
     "Storage", "Open-weave fruit basket, food-safe natural finish.", "bamboo basket, fruit, kitchen, eco friendly"),
    (1, "Bamboo Table Lamp", "Bamboo", "Handwoven", 980, 3, "MADE_TO_ORDER", 0,
     "Lighting", "Warm woven lampshade on a sturdy cane frame.", "bamboo lamp, lighting, decor, sustainable"),
    (2, "Terracotta Planter Set of 3", "Clay", "Hand-thrown Pottery", 690, 4, "STOCK", 15,
     "Planters", "Three graduated planters with drainage, kiln-fired.", "terracotta, planter, pottery, garden, handmade"),
    (2, "Terracotta Water Bottle — 1L", "Clay", "Hand-thrown Pottery", 540, 3, "STOCK", 20,
     "Kitchen", "Natural cooling clay bottle with cork stopper.", "terracotta, water bottle, clay, natural cooling"),
    (3, "Coir Doormat — Woven Pattern", "Coir", "Handwoven", 380, 2, "STOCK", 30,
     "Home", "Durable coir doormat with woven border pattern.", "coir, doormat, natural, eco friendly"),
    (3, "Coir Hanging Planter", "Coir", "Handwoven", 320, 2, "STOCK", 22,
     "Planters", "Liner basket for balconies, weather-resistant.", "coir, planter, hanging, garden"),
    (4, "Walnut Wood Serving Bowl", "Walnut Wood", "Hand Carving", 1350, 6, "MADE_TO_ORDER", 0,
     "Kitchen", "Carved from a single walnut block, food-safe oil finish.", "walnut, wood, bowl, carving, kashmir"),
    (4, "Chinar-Motif Wooden Box", "Walnut Wood", "Hand Carving", 890, 4, "STOCK", 8,
     "Decor", "Keepsake box with carved chinar-leaf lid.", "walnut, wood, box, carving, keepsake"),
    (5, "Dhokra Brass Bell — Medium", "Brass", "Dhokra Casting", 760, 5, "MADE_TO_ORDER", 0,
     "Decor", "Lost-wax cast bell with traditional motifs.", "dhokra, brass, bell, odisha, tribal craft"),
    (5, "Dhokra Brass Candle Stand", "Brass", "Dhokra Casting", 940, 6, "MADE_TO_ORDER", 0,
     "Lighting", "Cast candle stand, one of a kind.", "dhokra, brass, candle, decor"),
]

BUYERS = [
    {"name": "Anita Rao", "email": "anita@example.com", "type": "BUYER", "city": "Bengaluru"},
    {"name": "Vikram Shah", "email": "vikram@example.com", "type": "BUYER", "city": "Mumbai"},
    {"name": "BrightSpaces Gifting", "email": "orders@brightspaces.example.com", "type": "B2B_BUYER",
     "city": "Chennai", "business": "CORPORATE_GIFTING", "gst": "33ABCDE1234F1Z5"},
    {"name": "The Palm Hotel", "email": "procurement@palmhotel.example.com", "type": "B2B_BUYER",
     "city": "Kochi", "business": "HOTEL", "gst": "32Palmh5678K1Z2"},
]


def seed() -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    stats = {"artisans": 0, "products": 0, "orders": 0, "reviews": 0, "bulk": 0}

    if db.query(User).filter(User.is_demo.is_(True)).count() > 0:
        print(f"{DEMO_MARK} Demo data already present — skipping. Delete karvantana.db to reseed.")
        return stats

    try:
        # ---- taxonomy -----------------------------------------------------
        for lang in ("en", "ta", "hi", "te", "kn", "ml", "bn", "mr", "gu", "pa"):
            db.add(Language(code=lang, name=lang.upper()))
        cats = {}
        for name in ("Sarees", "Storage", "Planters", "Kitchen", "Home", "Decor", "Lighting"):
            cats[name] = Category(name=name, slug=name.lower())
            db.add(cats[name])
        crafts = {}
        for name in ("Handloom Weaving", "Bamboo Weaving", "Terracotta Pottery", "Coir Craft", "Wood Carving", "Dhokra Brass Casting"):
            crafts[name] = CraftType(name=name)
            db.add(crafts[name])
        db.flush()

        # ---- admin & cluster manager --------------------------------------
        admin = User(email="admin@karvantana.demo", full_name="Platform Admin (DEMO)",
                     hashed_password=hash_password("admin-demo-1234"), role="ADMIN", is_demo=True)
        manager = User(email="cluster@karvantana.demo", full_name="Kaveri Cluster Manager (DEMO)",
                       hashed_password=hash_password("cluster-demo-1234"), role="CLUSTER_MANAGER", is_demo=True)
        db.add_all([admin, manager])
        db.flush()
        cluster = Cluster(name="Kaveri Delta Artisan Cluster (DEMO)", region="Tamil Nadu",
                          manager_id=manager.id, description="Demo cluster for presentation.")
        db.add(cluster)
        db.flush()

        # ---- artisans -------------------------------------------------------
        artisan_profiles: list[ArtisanProfile] = []
        for i, spec in enumerate(ARTISANS):
            user = User(email=f"artisan{i+1}@karvantana.demo", full_name=f"{spec['person']} (DEMO)",
                        phone=f"98000{i:05d}"[:10] if False else None,
                        hashed_password=hash_password(f"artisan-demo-{i+1}"), role="ARTISAN", is_demo=True)
            db.add(user)
            db.flush()
            profile = ArtisanProfile(
                user_id=user.id, display_name=spec["name"], craft_specialization=spec["craft"],
                craft_story=spec["story"], village=spec["village"], district=spec["district"],
                state=spec["state"], years_of_experience=spec["years"], organization_type=spec["org"],
                production_capacity=random.choice([30, 50, 80, 120]), min_bulk_quantity=random.choice([10, 20, 50]),
                gst_registered=spec["org"] != "INDIVIDUAL", payment_ready=True,
                onboarding_step=3, onboarding_complete=True, verification_level="VERIFIED_ARTISAN",
                verification_status="VERIFIED", languages=spec["lang"],
                avatar_color=f"hsl({(i * 57) % 360}, 55%, 45%)",
            )
            db.add(profile)
            db.flush()
            artisan_profiles.append(profile)
            if i < 2:
                db.add(ClusterMember(cluster_id=cluster.id, artisan_id=profile.id))
        stats["artisans"] = len(artisan_profiles)

        # ---- products -------------------------------------------------------
        products: list[Product] = []
        for (aidx, title, material, technique, price, days, mode, stock, cat, line, keywords) in PRODUCTS:
            profile = artisan_profiles[aidx]
            img_bytes = _swatch(ARTISANS[aidx]["name"], *ARTISANS[aidx]["color"])
            url = _save(img_bytes, f"demo_p{len(products)}_a{aidx}.jpg")
            p = Product(
                artisan_id=profile.id, title=title,
                short_description=f"{line} {ARTISANS[aidx]['craft']} by {ARTISANS[aidx]['person']} of {ARTISANS[aidx]['village']}, {ARTISANS[aidx]['state']}.",
                description=(f"{line}\n\nEach piece is made by hand in {ARTISANS[aidx]['village']}, {ARTISANS[aidx]['district']}, "
                             f"by {ARTISANS[aidx]['person']}'s studio. As with all handmade work, small variations make every piece one of a kind.\n\n"
                             f"Care: wipe clean; keep away from prolonged moisture.\n"
                             f"Made-to-order in about {days} days." if mode == "MADE_TO_ORDER" else
                             f"{line}\n\nHandmade in {ARTISANS[aidx]['village']}, {ARTISANS[aidx]['state']}."),
                craft_story=ARTISANS[aidx]["story"],
                material=material, technique=technique, colour="Natural", origin=f"{ARTISANS[aidx]['district']}, {ARTISANS[aidx]['state']}",
                usage="everyday use and gifting", dimensions="30 x 30 x 12 cm", production_days=days,
                price=Decimal(price), inventory_mode=mode, stock_quantity=stock,
                moq=1, bulk_moq=10, bulk_price=Decimal(int(price * 0.88)), customization_available=bool(random.getrandbits(1)),
                lifecycle=ProductLifecycle.PUBLISHED, published_at=datetime.now(timezone.utc) - timedelta(days=random.randint(5, 40)),
                keywords=keywords, view_count=random.randint(5, 160),
            )
            p.category_id = cats[cat].id
            p.craft_type_id = crafts[ARTISANS[aidx]["craft"]].id
            db.add(p)
            db.flush()
            db.add(ProductImage(product_id=p.id, original_url=url, mime_type="image/jpeg",
                                size_bytes=len(img_bytes), quality_score=random.randint(78, 94),
                                is_primary=True, position=0))
            products.append(p)
        stats["products"] = len(products)

        # ---- buyers ---------------------------------------------------------
        buyers: list[User] = []
        for spec in BUYERS:
            u = User(email=spec["email"], full_name=f"{spec['name']} (DEMO)",
                     hashed_password=hash_password("buyer-demo-1234"), role=spec["type"], is_demo=True)
            db.add(u)
            db.flush()
            buyers.append(u)
            if spec["type"] == "BUYER":
                db.add(BuyerProfile(user_id=u.id, city=spec["city"]))
            else:
                db.add(BusinessProfile(user_id=u.id, business_name=spec["name"], buyer_type=spec["business"],
                                       gst_number=spec.get("gst"), city=spec["city"]))

        # ---- orders across history -----------------------------------------
        address = {"line1": "12 Rose Street", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001", "phone": "9800000000"}
        now = datetime.now(timezone.utc)
        for i in range(14):
            buyer = random.choice(buyers)
            picks = random.sample(products, k=random.randint(1, 2))
            subtotal = Decimal("0")
            lines = []
            for p in picks:
                qty = random.choice([1, 1, 2, 3])
                lines.append((p, qty))
                subtotal += p.price * qty
            created = now - timedelta(days=random.randint(1, 55))
            status = random.choices(
                [OrderStatus.COMPLETED, OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.IN_PRODUCTION, OrderStatus.CONFIRMED],
                weights=[7, 2, 2, 2, 2], k=1)[0]
            order = Order(order_number=f"KV-DEMO-{1000+i}", buyer_id=buyer.id, status=status,
                          subtotal=subtotal, shipping_fee=Decimal(0), platform_fee=(subtotal * Decimal("0.02")).quantize(Decimal("0.01")),
                          total=subtotal, shipping_address=address, created_at=created, updated_at=created)
            db.add(order)
            db.flush()
            for p, qty in lines:
                img = db.query(ProductImage).filter(ProductImage.product_id == p.id, ProductImage.is_primary.is_(True)).first()
                db.add(OrderItem(order_id=order.id, product_id=p.id, artisan_id=p.artisan_id,
                                 product_title_snapshot=p.title, product_image_url=img.original_url if img else None,
                                 unit_price=p.price, quantity=qty, line_total=p.price * qty))
            db.flush()
            db.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status=OrderStatus.CONFIRMED, changed_by=buyer.id, created_at=created))
            if status in (OrderStatus.COMPLETED, OrderStatus.DELIVERED):
                db.add(Payment(order_id=order.id, provider="demo", provider_payment_id=f"demo_pay_seed_{i}",
                               amount=order.total, status="CAPTURED", created_at=created))
            # reviews for completed orders
            if status == OrderStatus.COMPLETED and random.random() < 0.8:
                item = db.query(OrderItem).filter(OrderItem.order_id == order.id).first()
                db.add(Review(product_id=item.product_id, artisan_id=item.artisan_id, buyer_id=buyer.id,
                              order_item_id=item.id, product_rating=random.choices([5, 4, 3], weights=[7, 2, 1])[0],
                              text=random.choice([
                                  "Beautiful weave — even better than the photos. Packed carefully too.",
                                  "Sturdy and exactly the size I needed for my kitchen.",
                                  "Lovely finish. The artisan messaged me updates during production.",
                                  "Arrived quickly and the colour is gorgeous in daylight.",
                              ]),
                              is_verified_purchase=True, created_at=created + timedelta(days=4)))
                stats["reviews"] += 1
            stats["orders"] += 1

        # ---- repeat purchases (explicit story) ------------------------------
        anita = buyers[0]
        basket = products[2]
        for j, back in enumerate((40, 12)):
            subtotal = basket.price * 2
            order = Order(order_number=f"KV-DEMO-9{j}", buyer_id=anita.id, status=OrderStatus.COMPLETED,
                          subtotal=subtotal, shipping_fee=Decimal(0), platform_fee=Decimal(0), total=subtotal,
                          shipping_address=address, created_at=now - timedelta(days=back))
            db.add(order)
            db.flush()
            img = db.query(ProductImage).filter(ProductImage.product_id == basket.id, ProductImage.is_primary.is_(True)).first()
            db.add(OrderItem(order_id=order.id, product_id=basket.id, artisan_id=basket.artisan_id,
                             product_title_snapshot=basket.title, product_image_url=img.original_url if img else None,
                             unit_price=basket.price, quantity=2, line_total=subtotal))
            db.add(Payment(order_id=order.id, provider="demo", provider_payment_id=f"demo_pay_repeat_{j}",
                           amount=subtotal, status="CAPTURED"))
        db.add(Follow(user_id=anita.id, artisan_id=basket.artisan_id))
        db.add(SavedArtisan(user_id=anita.id, artisan_id=basket.artisan_id))

        # ---- B2B bulk request + quote --------------------------------------
        b2b = buyers[2]
        bulk = BulkRequest(buyer_id=b2b.id, title="Corporate Diwali gift hampers (DEMO)",
                           description="Handmade gift boxes for a corporate event; eco-friendly materials preferred.",
                           quantity=100, max_unit_price=Decimal(500), required_by=now + timedelta(days=30),
                           customization_required=True, category_hint="storage",
                           parsed_requirements={"quantity": 100, "max_unit_price": 500, "delivery_days": 30,
                                                "category": "STORAGE", "customization": True,
                                                "buyer_type": "CORPORATE", "confidence": 0.82},
                           status="OPEN")
        db.add(bulk)
        db.flush()
        q_product = products[2]
        db.add(Quote(request_type="BULK", request_id=bulk.id, artisan_id=q_product.artisan_id,
                     unit_price=Decimal(410), quantity=100, total=Decimal(41000), lead_time_days=21,
                     note="Includes kraft gift box and branded insert card.", status=QuoteStatus.PENDING,
                     expires_at=now + timedelta(days=14)))
        stats["bulk"] += 1

        # ---- custom request ---------------------------------------------------
        db.add(CustomRequest(buyer_id=buyers[0].id, artisan_id=artisan_profiles[0].id,
                             product_id=products[0].id, title="Wedding saree in family colours (DEMO)",
                             description="A handwoven saree in deep maroon and gold, similar to your natural-dye piece.",
                             quantity=1, budget=Decimal(2200), required_by=now + timedelta(days=45), status="OPEN"))

        # ---- reputation aggregates --------------------------------------------
        from app.services.review_service import review_service

        db.flush()
        for profile in artisan_profiles:
            review_service._recompute_artisan_reputation(db, profile.id)

        db.commit()
        print(f"{DEMO_MARK} Seeded: {stats['artisans']} artisans, {stats['products']} products, "
              f"{stats['orders']}+2 orders, {stats['reviews']} reviews, {stats['bulk']} bulk request,")
        print(f"{DEMO_MARK} Logins — artisan1@karvantana.demo / artisan-demo-1 · anita@example.com / buyer-demo-1234 ·")
        print(f"          orders@brightspaces.example.com / buyer-demo-1234 · admin@karvantana.demo / admin-demo-1234")
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
