"""
Development Seed Data Script for NagarSetu.
Seeds:
- 8 Municipal Departments (Roads, Water, Sanitation, Sewerage, Electrical, Parks, Public Health, Other)
- 18+ Department-Linked Categories with Subcategories
- 10+ Locality Gazetteer entries with multiple aliases (including MP Nagar variations)
- 32 Synthetic Multilingual Complaints (English, Hindi, Hinglish across 4 civic channels)
- Duplicate Clusters and Cluster Members
- Operator Acknowledgements (draft, edited, approved)
- Status History Audit Trails
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal, engine
from app.db.init_db import create_tables
from app.models.taxonomy import Department, Category
from app.models.gazetteer import LocalityGazetteer, LocalityAlias
from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory
from app.models.cluster import DuplicateCluster, ClusterMember
from app.models.acknowledgement import Acknowledgement
from app.models.analytics import WeeklyReport, EvaluationResult


def seed_departments(db) -> dict:
    print("Seeding 8 municipal departments...")
    departments_data = [
        {
            "department_id": "DEPT_ROADS",
            "code": "RDS",
            "name": "Roads & Infrastructure",
            "description": "Maintenance of municipal carriageways, dividers, footpaths, bridges, and culverts.",
            "default_sla_hours": 48,
            "escalation_contact": "ee-roads@municipality.gov.in"
        },
        {
            "department_id": "DEPT_WATER",
            "code": "WSS_WATER",
            "name": "Water Supply",
            "description": "Potable piped water distribution, pipeline bursts, leakages, and water pressure.",
            "default_sla_hours": 12,
            "escalation_contact": "ee-water@municipality.gov.in"
        },
        {
            "department_id": "DEPT_SANITATION",
            "code": "SWM",
            "name": "Sanitation & Solid Waste",
            "description": "Door-to-door garbage collection, community dumpsters, street sweeping, and litter.",
            "default_sla_hours": 24,
            "escalation_contact": "ee-sanitation@municipality.gov.in"
        },
        {
            "department_id": "DEPT_SEWERAGE",
            "code": "WSS_SEWER",
            "name": "Sewerage & Drainage",
            "description": "Underground sewer networks, manhole covers, drain clearing, and storm runoffs.",
            "default_sla_hours": 8,
            "escalation_contact": "ee-sewerage@municipality.gov.in"
        },
        {
            "department_id": "DEPT_ELECTRICAL",
            "code": "ELEC",
            "name": "Electrical & Street Lighting",
            "description": "Public lighting poles, feeder panels, sodium/LED lamps, and exposed wires.",
            "default_sla_hours": 24,
            "escalation_contact": "ee-electrical@municipality.gov.in"
        },
        {
            "department_id": "DEPT_PARKS",
            "code": "HORT",
            "name": "Parks & Horticulture",
            "description": "Municipal gardens, children's play equipment, grass trimming, and tree pruning.",
            "default_sla_hours": 48,
            "escalation_contact": "dd-parks@municipality.gov.in"
        },
        {
            "department_id": "DEPT_PUBLIC_HEALTH",
            "code": "HLT",
            "name": "Public Health & Sanitation Hazards",
            "description": "Anti-larval fogging, dengue/malaria prevention, stray animal vaccination, and food stalls.",
            "default_sla_hours": 24,
            "escalation_contact": "health-officer@municipality.gov.in"
        },
        {
            "department_id": "DEPT_OTHER",
            "code": "GEN",
            "name": "General Administration & Other",
            "description": "Unclassified grievances, miscellaneous civic requests, and citizen inquiries.",
            "default_sla_hours": 72,
            "escalation_contact": "central-triage@municipality.gov.in"
        }
    ]

    dept_map = {}
    for d in departments_data:
        dept = db.query(Department).filter(Department.department_id == d["department_id"]).first()
        if not dept:
            dept = Department(**d)
            db.add(dept)
        dept_map[d["department_id"]] = dept
    db.commit()
    return dept_map


def seed_categories(db, dept_map) -> dict:
    print("Seeding 19 department-linked categories...")
    categories_data = [
        # Roads (4 categories)
        {
            "category_id": "CAT_POTHOLE",
            "department_id": "DEPT_ROADS",
            "name": "Pothole",
            "description": "Dangerous potholes and road craters.",
            "typical_sla_hours": 24,
            "subcategories": ["Deep carriageway crater", "Surface erosion", "Monsoon pothole cluster"]
        },
        {
            "category_id": "CAT_ROAD_DAMAGE",
            "department_id": "DEPT_ROADS",
            "name": "Road Damage",
            "description": "Caved-in asphalt, damaged dividers, or sinking subgrade.",
            "typical_sla_hours": 48,
            "subcategories": ["Road cave-in", "Broken median divider", "Damaged speed breaker"]
        },
        {
            "category_id": "CAT_FOOTPATH_DAMAGE",
            "department_id": "DEPT_ROADS",
            "name": "Footpath Damage",
            "description": "Broken sidewalk tiles, missing slabs, and pedestrian obstructions.",
            "typical_sla_hours": 72,
            "subcategories": ["Missing paver blocks", "Damaged footpath kerb", "Uncovered utility duct"]
        },
        {
            "category_id": "CAT_ROAD_OBSTRUCTION",
            "department_id": "DEPT_ROADS",
            "name": "Road Obstruction",
            "description": "Construction debris or heavy materials dumped on roadway.",
            "typical_sla_hours": 24,
            "subcategories": ["Illegal construction material", "Fallen hoarding", "Abandoned barrier"]
        },

        # Water (3 categories)
        {
            "category_id": "CAT_WATER_LEAKAGE",
            "department_id": "DEPT_WATER",
            "name": "Water Leakage",
            "description": "Main water pipeline burst, distribution leak, or leaking valve.",
            "typical_sla_hours": 8,
            "subcategories": ["Underground pipeline burst", "Gushing main supply line", "Leaking sluice valve"]
        },
        {
            "category_id": "CAT_NO_WATER_SUPPLY",
            "department_id": "DEPT_WATER",
            "name": "No Water Supply",
            "description": "Colony-wide disruption or low pressure drinking water.",
            "typical_sla_hours": 12,
            "subcategories": ["Complete supply outage", "Extremely low pressure", "Irregular timing"]
        },
        {
            "category_id": "CAT_WATER_QUALITY",
            "department_id": "DEPT_WATER",
            "name": "Water Quality",
            "description": "Contaminated, muddy, or foul-smelling tap water.",
            "typical_sla_hours": 6,
            "subcategories": ["Sewage mixed with drinking water", "Yellow/turbid water", "Foul chemical odor"]
        },

        # Sanitation (3 categories)
        {
            "category_id": "CAT_GARBAGE_COLLECTION",
            "department_id": "DEPT_SANITATION",
            "name": "Garbage Collection",
            "description": "Door-to-door waste vehicle missed or delayed.",
            "typical_sla_hours": 12,
            "subcategories": ["Door-to-door vehicle absent 3+ days", "Commercial market waste uncollected"]
        },
        {
            "category_id": "CAT_GARBAGE_DUMP",
            "department_id": "DEPT_SANITATION",
            "name": "Garbage Dump",
            "description": "Overflowing dhalao, open garbage pile, or illegal roadside dumping.",
            "typical_sla_hours": 8,
            "subcategories": ["Dhalao overflowing on road", "Vacant plot garbage dump", "Rotting organic waste"]
        },
        {
            "category_id": "CAT_SANITATION_ISSUE",
            "department_id": "DEPT_SANITATION",
            "name": "Sanitation Issue",
            "description": "Unswept streets, littering around markets, dead animals.",
            "typical_sla_hours": 12,
            "subcategories": ["Animal carcass removal", "Littered market area", "Unswept primary avenue"]
        },

        # Sewerage (3 categories)
        {
            "category_id": "CAT_SEWER_OVERFLOW",
            "department_id": "DEPT_SEWERAGE",
            "name": "Sewer Overflow",
            "description": "Sewage water flooding onto public streets.",
            "typical_sla_hours": 4,
            "subcategories": ["Choked sewer bubbling on street", "Backflow into residential compound"]
        },
        {
            "category_id": "CAT_SEWER_BLOCKAGE",
            "department_id": "DEPT_SEWERAGE",
            "name": "Sewer Blockage",
            "description": "Blocked sewer pipeline or clogged storm water drain.",
            "typical_sla_hours": 8,
            "subcategories": ["Underground line blocked", "Monsoon storm drain clogged with silt"]
        },
        {
            "category_id": "CAT_OPEN_MANHOLE",
            "department_id": "DEPT_SEWERAGE",
            "name": "Open Manhole",
            "description": "Missing, cracked, or displaced manhole cover.",
            "typical_sla_hours": 2,
            "subcategories": ["Missing cover on main carriageway", "Broken concrete lid", "Displaced chamber"]
        },

        # Electrical (2 categories)
        {
            "category_id": "CAT_STREET_LIGHT_FAILURE",
            "department_id": "DEPT_ELECTRICAL",
            "name": "Street Light Failure",
            "description": "Non-functional streetlights or dark stretches.",
            "typical_sla_hours": 24,
            "subcategories": ["Entire lane in darkness", "Single bulb fused", "Flickering high mast light"]
        },
        {
            "category_id": "CAT_DAMAGED_ELECTRICAL_POLE",
            "department_id": "DEPT_ELECTRICAL",
            "name": "Damaged Electrical Pole",
            "description": "Bent pole, exposed wires, sparking transformer.",
            "typical_sla_hours": 2,
            "subcategories": ["Sparking overhead line", "Exposed hanging cable near ground", "Bent pole after accident"]
        },

        # Parks (2 categories)
        {
            "category_id": "CAT_PARK_MAINTENANCE",
            "department_id": "DEPT_PARKS",
            "name": "Park Maintenance",
            "description": "Overgrown weeds, dry lawns, unpruned tree branches.",
            "typical_sla_hours": 48,
            "subcategories": ["Uncut grass and wild bushes", "Hazardous hanging tree limb", "Unmaintained jogging track"]
        },
        {
            "category_id": "CAT_BROKEN_PARK_EQUIPMENT",
            "department_id": "DEPT_PARKS",
            "name": "Broken Park Equipment",
            "description": "Damaged children's swings, broken benches, open garden lighting.",
            "typical_sla_hours": 72,
            "subcategories": ["Broken swing / slide", "Damaged concrete park bench", "Broken perimeter fence"]
        },

        # Public Health (2 categories)
        {
            "category_id": "CAT_SANITATION_HAZARD",
            "department_id": "DEPT_PUBLIC_HEALTH",
            "name": "Sanitation Hazard",
            "description": "Stagnant foul water puddles causing severe health risks.",
            "typical_sla_hours": 12,
            "subcategories": ["Stagnant green cesspool", "Uncovered chemical effluent"]
        },
        {
            "category_id": "CAT_MOSQUITO_VECTOR_ISSUE",
            "department_id": "DEPT_PUBLIC_HEALTH",
            "name": "Mosquito / Vector Issue",
            "description": "Mosquito breeding, malaria/dengue spike, fogging requirement.",
            "typical_sla_hours": 24,
            "subcategories": ["Anti-larval fogging request", "Dengue outbreak report in locality"]
        }
    ]

    cat_map = {}
    for c in categories_data:
        cat = db.query(Category).filter(Category.category_id == c["category_id"]).first()
        if not cat:
            cat = Category(**c)
            db.add(cat)
        cat_map[c["category_id"]] = cat
    db.commit()
    return cat_map


def seed_gazetteer(db) -> dict:
    print("Seeding 10+ locality gazetteer records with rich alias mappings (including MP Nagar)...")
    localities_data = [
        {
            "canonical_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "aliases": ["MP Nagar", "M.P. Nagar", "MPNagar", "M P Nagar", "Maharana Pratap Nagar", "Zone 1 MP Nagar", "Zone 2 MP Nagar"],
            "landmarks": [
                {"name": "Sargam Cinema", "type": "commercial"},
                {"name": "City Plaza", "type": "transit"},
                {"name": "Coaching Hub", "type": "education"}
            ]
        },
        {
            "canonical_locality": "Shivaji Nagar",
            "ward": "Ward 101",
            "zone": "Central Zone",
            "aliases": ["Shivaji Nagar", "Shivajinagar", "Shivaji Nagar Sector A", "Shivaji Nagar Sector B", "6 Number Stop"],
            "landmarks": [
                {"name": "District Civil Hospital", "type": "hospital"},
                {"name": "Shivaji Government School", "type": "school"},
                {"name": "Shivaji Mandir", "type": "religious"}
            ]
        },
        {
            "canonical_locality": "Gandhi Chowk",
            "ward": "Ward 102",
            "zone": "Central Zone",
            "aliases": ["Gandhi Chowk", "Ghanta Ghar", "Clock Tower Market", "Subhash Marg Chowk", "Gandhi Circle"],
            "landmarks": [
                {"name": "Clock Tower", "type": "heritage"},
                {"name": "City Dispensary", "type": "hospital"}
            ]
        },
        {
            "canonical_locality": "Vasant Vihar",
            "ward": "Ward 201",
            "zone": "South Zone",
            "aliases": ["Vasant Vihar", "Basant Vihar", "Vasant Kunj Extension", "Lakeview Colony Vasant Vihar"],
            "landmarks": [
                {"name": "St. Mary's Public School", "type": "school"},
                {"name": "Community Health Post", "type": "hospital"}
            ]
        },
        {
            "canonical_locality": "Indira Industrial Area",
            "ward": "Ward 202",
            "zone": "South Zone",
            "aliases": ["Indira Industrial Area", "Industrial Area Phase 1", "Indiranagar Industrial", "Transport Nagar Area"],
            "landmarks": [
                {"name": "ESI Hospital", "type": "hospital"},
                {"name": "CETP Treatment Plant", "type": "utility"}
            ]
        },
        {
            "canonical_locality": "Nehru Market",
            "ward": "Ward 103",
            "zone": "Central Zone",
            "aliases": ["Nehru Market", "Nehru Bazaar", "Old Grain Market", "Nehru Chowk Market"],
            "landmarks": [
                {"name": "Vegetable Mandi", "type": "commercial"},
                {"name": "Central Post Office", "type": "public_facility"}
            ]
        },
        {
            "canonical_locality": "Civil Lines",
            "ward": "Ward 301",
            "zone": "North Zone",
            "aliases": ["Civil Lines", "Civil Line", "Court Road Area", "Collectorate Road", "Officers Colony"],
            "landmarks": [
                {"name": "District Collectorate", "type": "government"},
                {"name": "Session Court", "type": "government"}
            ]
        },
        {
            "canonical_locality": "Subhash Nagar",
            "ward": "Ward 302",
            "zone": "North Zone",
            "aliases": ["Subhash Nagar", "Subhashnagar", "Railway Crossing Subhash Nagar", "Subhash Colony"],
            "landmarks": [
                {"name": "Railway Overbridge", "type": "infrastructure"},
                {"name": "Government Polytech", "type": "education"}
            ]
        },
        {
            "canonical_locality": "Railway Colony",
            "ward": "Ward 104",
            "zone": "Central Zone",
            "aliases": ["Railway Colony", "Station Road Colony", "Platform Road", "Loco Shed Colony"],
            "landmarks": [
                {"name": "Railway Junction Station", "type": "transit"},
                {"name": "Railway Divisional Hospital", "type": "hospital"}
            ]
        },
        {
            "canonical_locality": "Green Park",
            "ward": "Ward 203",
            "zone": "South Zone",
            "aliases": ["Green Park", "Green Park Enclave", "Green Park Extension", "South Green Park"],
            "landmarks": [
                {"name": "Green Park Botanical Garden", "type": "park"},
                {"name": "Green Park Club House", "type": "recreation"}
            ]
        },
        {
            "canonical_locality": "Shahpura",
            "ward": "Ward 14",
            "zone": "South Zone",
            "aliases": ["Shahpura", "Shahpura Sector B", "Shahpura Lake", "वार्ड 14", "Ward 14"],
            "landmarks": [
                {"name": "Shahpura Lake", "type": "park"},
                {"name": "Shahpura Community Hall", "type": "public_facility"}
            ]
        },
        {
            "canonical_locality": "Arera Colony",
            "ward": "Ward 48",
            "zone": "South Zone",
            "aliases": ["Arera Colony", "Arera Colony E-7", "10 Number Market", "10 No Market", "E-7 Arera Colony", "Arera"],
            "landmarks": [
                {"name": "10 Number Market", "type": "commercial"},
                {"name": "National Hospital", "type": "hospital"}
            ]
        },
        {
            "canonical_locality": "Bittan Market",
            "ward": "Ward 45",
            "zone": "South Zone",
            "aliases": ["Bittan Market", "Bittan Market Taxi Stand", "Bittan Bazaar", "Bittan Haat"],
            "landmarks": [
                {"name": "Bittan Market Ground", "type": "commercial"},
                {"name": "Bittan Taxi Stand", "type": "transit"}
            ]
        },
        {
            "canonical_locality": "Kolar Road",
            "ward": "Ward 80",
            "zone": "South Zone",
            "aliases": ["Kolar Road", "Kolar", "Kolar Main Road"],
            "landmarks": [
                {"name": "Kolar Petrol Pump", "type": "transit"}
            ]
        },
        {
            "canonical_locality": "Bawadiya Kalan",
            "ward": "Ward 52",
            "zone": "South Zone",
            "aliases": ["Bawadiya Kalan", "Bawadiya"],
            "landmarks": [
                {"name": "Bawadiya Overbridge", "type": "infrastructure"}
            ]
        },
        {
            "canonical_locality": "New Market",
            "ward": "Ward 30",
            "zone": "Central Zone",
            "aliases": ["New Market", "Top n Town New Market", "New Market TT Nagar"],
            "landmarks": [
                {"name": "TT Nagar Stadium", "type": "public_facility"}
            ]
        },
        {
            "canonical_locality": "Hoshangabad Road",
            "ward": "Ward 55",
            "zone": "South Zone",
            "aliases": ["Hoshangabad Road", "Hoshangabad Highway"],
            "landmarks": [
                {"name": "Aashima Mall", "type": "commercial"}
            ]
        },
        {
            "canonical_locality": "Indira Nagar",
            "ward": "Ward 202",
            "zone": "South Zone",
            "aliases": ["Indira Nagar", "Indiranagar", "Indira Colony"],
            "landmarks": [
                {"name": "Indira Nagar Water Tank", "type": "utility"}
            ]
        }
    ]

    gazetteer_map = {}
    for loc_data in localities_data:
        record = db.query(LocalityGazetteer).filter(LocalityGazetteer.canonical_locality == loc_data["canonical_locality"]).first()
        if not record:
            record = LocalityGazetteer(
                canonical_locality=loc_data["canonical_locality"],
                ward=loc_data["ward"],
                zone=loc_data["zone"],
                aliases=loc_data["aliases"],
                landmarks=loc_data["landmarks"],
                is_active=True
            )
            db.add(record)
            db.flush()

        # Seed normalized alias entries
        for alias_str in loc_data["aliases"]:
            norm_alias = alias_str.strip().lower()
            existing_alias = db.query(LocalityAlias).filter(LocalityAlias.alias_normalized == norm_alias).first()
            if not existing_alias:
                db.add(LocalityAlias(
                    alias_normalized=norm_alias,
                    gazetteer_id=record.id,
                    canonical_locality=loc_data["canonical_locality"]
                ))

        gazetteer_map[loc_data["canonical_locality"]] = record

    db.commit()
    return gazetteer_map


def seed_synthetic_complaints(db):
    if db.query(RawComplaint).first():
        print("Synthetic complaints already seeded. Skipping.")
        return

    print("Seeding 32 synthetic complaints across English, Hindi, and Hinglish across 4 channels...")

    # Define base timestamp window
    base_time = datetime.now(timezone.utc) - timedelta(days=5)

    # 32 Realistic Synthetic Complaints
    raw_data = [
        # --- ENGLISH COMPLAINTS ---
        {
            "id": "CMP-SYN-001",
            "time_offset_hrs": 1,
            "channel": "municipal_app",
            "text": "Huge pothole in front of Sargam Cinema in MP Nagar. Two two-wheelers skidded this morning.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/pothole_mp_nagar.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Photograph showing deep crater on asphalt carriageway near Sargam Cinema",
            "source_location": "MP Nagar near Sargam",
            "dept": "DEPT_ROADS",
            "cat": "CAT_POTHOLE",
            "subcat": "Deep carriageway crater",
            "urgency": "HIGH",
            "score": 0.85,
            "reason": "Accident hazard: Road crater near busy commercial market causing two-wheeler skids.",
            "loc": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "lang": "en",
            "summary": "Dangerous pothole near Sargam Cinema causing vehicular accidents."
        },
        {
            "id": "CMP-SYN-002",
            "time_offset_hrs": 2,
            "channel": "state_helpline",
            "text": "Deep open manhole without any barricade or lid on main road in M.P. Nagar Zone 1. Very dangerous for children.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/open_manhole.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Missing round iron manhole cover on busy road",
            "source_location": "M.P. Nagar Zone 1",
            "dept": "DEPT_SEWERAGE",
            "cat": "CAT_OPEN_MANHOLE",
            "subcat": "Missing cover on main carriageway",
            "urgency": "CRITICAL",
            "score": 0.98,
            "reason": "Public life hazard: Uncovered open manhole on active traffic road without warning barrier.",
            "loc": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "lang": "en",
            "summary": "Uncovered open manhole on main road in M.P. Nagar Zone 1."
        },
        {
            "id": "CMP-SYN-003",
            "time_offset_hrs": 3,
            "channel": "social_media",
            "text": "Major drinking water pipeline burst in Shivaji Nagar Sector A. Fresh water flooding the street for 6 hours.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/pipe_burst.jpg",
            "image_caption": "[SYNTHETIC_DEMO] High pressure water geyser erupting from broken street line",
            "source_location": "Shivaji Nagar Sector A",
            "dept": "DEPT_WATER",
            "cat": "CAT_WATER_LEAKAGE",
            "subcat": "Gushing main supply line",
            "urgency": "HIGH",
            "score": 0.88,
            "reason": "Major utility loss: Gushing potable water main flooding residential street.",
            "loc": "Shivaji Nagar",
            "ward": "Ward 101",
            "zone": "Central Zone",
            "lang": "en",
            "summary": "Main water pipeline burst flooding residential lane in Shivaji Nagar."
        },
        {
            "id": "CMP-SYN-004",
            "time_offset_hrs": 4,
            "channel": "elected_rep_message",
            "text": "Streetlights non-functional from Clock Tower to Subhash Marg in Gandhi Chowk. Complete pitch darkness for 3 nights.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Gandhi Chowk Clock Tower",
            "dept": "DEPT_ELECTRICAL",
            "cat": "CAT_STREET_LIGHT_FAILURE",
            "subcat": "Entire lane in darkness",
            "urgency": "MEDIUM",
            "score": 0.65,
            "reason": "Public security concern: Continuous streetlight outage on commercial market stretch.",
            "loc": "Gandhi Chowk",
            "ward": "Ward 102",
            "zone": "Central Zone",
            "lang": "en",
            "summary": "Complete streetlight failure from Clock Tower to Subhash Marg for 3 nights."
        },
        {
            "id": "CMP-SYN-005",
            "time_offset_hrs": 5,
            "channel": "municipal_app",
            "text": "Community garbage bin overflowing in Vasant Vihar Block C. Stray dogs scattering waste all over road.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/dumpster_overflow.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Overflowing metallic municipal dustbin with waste spill",
            "source_location": "Vasant Vihar Block C",
            "dept": "DEPT_SANITATION",
            "cat": "CAT_GARBAGE_DUMP",
            "subcat": "Dhalao overflowing on road",
            "urgency": "MEDIUM",
            "score": 0.58,
            "reason": "Sanitation vector nuisance: Rotting garbage pile attracting stray animals.",
            "loc": "Vasant Vihar",
            "ward": "Ward 201",
            "zone": "South Zone",
            "lang": "en",
            "summary": "Overflowing public dumpster in Vasant Vihar creating sanitation nuisance."
        },
        {
            "id": "CMP-SYN-006",
            "time_offset_hrs": 6,
            "channel": "state_helpline",
            "text": "Live electrical wire snapped and hanging dangerously low across footpath near St. Mary's School in Vasant Vihar.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/live_wire.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Loose black power wire dangling within reach of pedestrians",
            "source_location": "Near St Marys School Vasant Vihar",
            "dept": "DEPT_ELECTRICAL",
            "cat": "CAT_DAMAGED_ELECTRICAL_POLE",
            "subcat": "Exposed hanging cable near ground",
            "urgency": "CRITICAL",
            "score": 0.99,
            "reason": "Deterministic hazard override: Live electrical wire hanging near primary school.",
            "loc": "Vasant Vihar",
            "ward": "Ward 201",
            "zone": "South Zone",
            "lang": "en",
            "summary": "Exposed live wire hanging near school walkway in Vasant Vihar."
        },
        {
            "id": "CMP-SYN-007",
            "time_offset_hrs": 7,
            "channel": "municipal_app",
            "text": "Sewage drain backed up and dark black water flooding into basements in Indira Industrial Area Phase 1.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Phase 1 Indira Industrial",
            "dept": "DEPT_SEWERAGE",
            "cat": "CAT_SEWER_OVERFLOW",
            "subcat": "Backflow into residential compound",
            "urgency": "HIGH",
            "score": 0.82,
            "reason": "Severe civic disruption: Industrial sewer water flooding commercial basements.",
            "loc": "Indira Industrial Area",
            "ward": "Ward 202",
            "zone": "South Zone",
            "lang": "en",
            "summary": "Sewer overflow flooding basements in Indira Industrial Area."
        },
        {
            "id": "CMP-SYN-008",
            "time_offset_hrs": 8,
            "channel": "social_media",
            "text": "Broken children's slide and damaged swings in Green Park botanical garden. Sharp iron edges exposed.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/broken_swings.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Broken metallic slide with rust and sharp edges in playground",
            "source_location": "Green Park Garden",
            "dept": "DEPT_PARKS",
            "cat": "CAT_BROKEN_PARK_EQUIPMENT",
            "subcat": "Broken swing / slide",
            "urgency": "MEDIUM",
            "score": 0.52,
            "reason": "Child safety concern: Exposed rusted jagged edges on public playground equipment.",
            "loc": "Green Park",
            "ward": "Ward 203",
            "zone": "South Zone",
            "lang": "en",
            "summary": "Damaged playground swings and slide with sharp edges in Green Park."
        },
        {
            "id": "CMP-SYN-009",
            "time_offset_hrs": 9,
            "channel": "elected_rep_message",
            "text": "Stagnant cesspool of rainwater behind vegetable mandi in Nehru Market. Severe mosquito menace, residents fear dengue.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Nehru Market Sabzi Mandi",
            "dept": "DEPT_PUBLIC_HEALTH",
            "cat": "CAT_MOSQUITO_VECTOR_ISSUE",
            "subcat": "Anti-larval fogging request",
            "urgency": "HIGH",
            "score": 0.79,
            "reason": "Vector outbreak threat: Extensive stagnant cesspool generating mosquito swarms.",
            "loc": "Nehru Market",
            "ward": "Ward 103",
            "zone": "Central Zone",
            "lang": "en",
            "summary": "Stagnant cesspool behind vegetable market causing mosquito breeding risk."
        },
        {
            "id": "CMP-SYN-010",
            "time_offset_hrs": 10,
            "channel": "municipal_app",
            "text": "Broken footpath pavement blocks on Court Road in Civil Lines. Elderly citizens stumbling regularly.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Civil Lines Court Road",
            "dept": "DEPT_ROADS",
            "cat": "CAT_FOOTPATH_DAMAGE",
            "subcat": "Missing paver blocks",
            "urgency": "LOW",
            "score": 0.38,
            "reason": "Routine pedestrian maintenance: Dislodged sidewalk pavers without acute hazard.",
            "loc": "Civil Lines",
            "ward": "Ward 301",
            "zone": "North Zone",
            "lang": "en",
            "summary": "Dislodged pavement blocks along Court Road sidewalk in Civil Lines."
        },

        # --- HINDI COMPLAINTS ---
        {
            "id": "CMP-SYN-011",
            "time_offset_hrs": 11,
            "channel": "state_helpline",
            "text": "शिवाजी नगर सेक्टर बी में पिछले तीन दिनों से पीने का पानी नहीं आया है। पानी का टैंकर भी नहीं भेजा गया।",
            "audio_path": "data/raw/synthetic/audio_no_water_hi.mp3",
            "image_path": None,
            "image_caption": None,
            "source_location": "शिवाजी नगर सेक्टर बी",
            "dept": "DEPT_WATER",
            "cat": "CAT_NO_WATER_SUPPLY",
            "subcat": "Complete supply outage",
            "urgency": "HIGH",
            "score": 0.86,
            "reason": "Essential resource disruption: Complete piped water supply disruption for 72 hours.",
            "loc": "Shivaji Nagar",
            "ward": "Ward 101",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "शिवाजी नगर सेक्टर बी में 3 दिनों से जलापूर्ति ठप, टैंकर की मांग।"
        },
        {
            "id": "CMP-SYN-012",
            "time_offset_hrs": 12,
            "channel": "municipal_app",
            "text": "घंटा घर चौक गांधी चौक के पास सीवर का गंदा पानी सड़क पर बह रहा है, बदबू से दुकानदारों का बैठना मुश्किल हो गया है।",
            "audio_path": None,
            "image_path": "data/raw/synthetic/sewer_hi.jpg",
            "image_caption": "[SYNTHETIC_DEMO] गंदा सीवर का पानी मुख्य बाजार में भरा हुआ",
            "source_location": "गांधी चौक घंटा घर",
            "dept": "DEPT_SEWERAGE",
            "cat": "CAT_SEWER_OVERFLOW",
            "subcat": "Choked sewer bubbling on street",
            "urgency": "HIGH",
            "score": 0.81,
            "reason": "Sanitation contamination: Raw sewage spilling directly into primary commercial bazaar.",
            "loc": "Gandhi Chowk",
            "ward": "Ward 102",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "गांधी चौक घंटा घर के पास सीवर ओवरफ्लो, सड़क पर गंदा पानी।"
        },
        {
            "id": "CMP-SYN-013",
            "time_offset_hrs": 13,
            "channel": "social_media",
            "text": "एम.पी. नगर जोन 2 में सड़क पर इतना बड़ा गड्ढा हो गया है कि कार का पहिया धंस गया। तुरंत मरम्मत कराई जाए।",
            "audio_path": None,
            "image_path": "data/raw/synthetic/car_pothole.jpg",
            "image_caption": "[SYNTHETIC_DEMO] कार का टायर गड्ढे में फंसा हुआ",
            "source_location": "M.P. Nagar Zone 2",
            "dept": "DEPT_ROADS",
            "cat": "CAT_POTHOLE",
            "subcat": "Deep carriageway crater",
            "urgency": "HIGH",
            "score": 0.77,
            "reason": "Traffic disruption: Deep crater trapping vehicular tires in MP Nagar Zone 2.",
            "loc": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "एम.पी. नगर जोन 2 में बड़ा गड्ढा, वाहन दुर्घटना की आशंका।"
        },
        {
            "id": "CMP-SYN-014",
            "time_offset_hrs": 14,
            "channel": "state_helpline",
            "text": "सुभाष नगर रेलवे क्रॉसिंग के पास एक आवारा जानवर मरा पड़ा है। दुर्गंध के कारण राहगीरों का निकलना दूभर हो गया है।",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "सुभाष नगर रेलवे फाटक",
            "dept": "DEPT_SANITATION",
            "cat": "CAT_SANITATION_ISSUE",
            "subcat": "Animal carcass removal",
            "urgency": "HIGH",
            "score": 0.78,
            "reason": "Sanitation urgency rule: Deceased animal carcass decomposing in public transit area.",
            "loc": "Subhash Nagar",
            "ward": "Ward 302",
            "zone": "North Zone",
            "lang": "hi",
            "summary": "सुभाष नगर रेलवे क्रॉसिंग पर मृत पशु का शव, तत्काल उठाने की मांग।"
        },
        {
            "id": "CMP-SYN-015",
            "time_offset_hrs": 15,
            "channel": "elected_rep_message",
            "text": "रेलवे कॉलोनी प्लेटफार्म रोड पर बिजली का खंभा झुक गया है और तार बहुत नीचे आ गए हैं। हादसा हो सकता है।",
            "audio_path": None,
            "image_path": "data/raw/synthetic/tilted_pole.jpg",
            "image_caption": "[SYNTHETIC_DEMO] झुका हुआ बिजली का खंभा",
            "source_location": "रेलवे कॉलोनी प्लेटफार्म रोड",
            "dept": "DEPT_ELECTRICAL",
            "cat": "CAT_DAMAGED_ELECTRICAL_POLE",
            "subcat": "Bent pole after accident",
            "urgency": "CRITICAL",
            "score": 0.94,
            "reason": "Immediate structural hazard: Tilted electrical pole with sagging conductors over road.",
            "loc": "Railway Colony",
            "ward": "Ward 104",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "रेलवे कॉलोनी में झुका हुआ विद्युत पोल एवं ढीले तार, दुर्घटना की संभावना।"
        },
        {
            "id": "CMP-SYN-016",
            "time_offset_hrs": 16,
            "channel": "municipal_app",
            "text": "नेहरू मार्केट में पिछले एक हफ्ते से कचरा गाड़ी नहीं आई है। पूरी गली में कूड़ा फैला हुआ है।",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "नेहरू बाजार पुरानी अनाज मंडी",
            "dept": "DEPT_SANITATION",
            "cat": "CAT_GARBAGE_COLLECTION",
            "subcat": "Door-to-door vehicle absent 3+ days",
            "urgency": "MEDIUM",
            "score": 0.62,
            "reason": "Delayed municipal service: Waste collection vehicle missed residential lane for 7 days.",
            "loc": "Nehru Market",
            "ward": "Ward 103",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "नेहरू मार्केट में एक सप्ताह से कूड़ा उठाने वाली गाड़ी अनुपस्थित।"
        },
        {
            "id": "CMP-SYN-017",
            "time_offset_hrs": 17,
            "channel": "state_helpline",
            "text": "सिविल लाइंस कलेक्ट्रेट रोड पर पानी के नल से मटमैला और बदबूदार पानी आ रहा है। पीने लायक नहीं है।",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "सिविल लाइन्स कलेक्ट्रेट",
            "dept": "DEPT_WATER",
            "cat": "CAT_WATER_QUALITY",
            "subcat": "Yellow/turbid water",
            "urgency": "HIGH",
            "score": 0.84,
            "reason": "Public health risk: Tap water contamination reported in administrative residential area.",
            "loc": "Civil Lines",
            "ward": "Ward 301",
            "zone": "North Zone",
            "lang": "hi",
            "summary": "सिविल लाइंस में नलों में आ रहा मटमैला और बदबूदार पेयजल।"
        },
        {
            "id": "CMP-SYN-018",
            "time_offset_hrs": 18,
            "channel": "municipal_app",
            "text": "ग्रीन पार्क में घास और झाड़ियां बहुत बड़ी हो गई हैं, जहरीले कीड़े निकल रहे हैं। पार्क की कटाई-सफाई करवाएं।",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "ग्रीन पार्क एक्सटेंशन",
            "dept": "DEPT_PARKS",
            "cat": "CAT_PARK_MAINTENANCE",
            "subcat": "Uncut grass and wild bushes",
            "urgency": "LOW",
            "score": 0.35,
            "reason": "Standard horticulture request: Wild vegetation overgrowth in municipal park.",
            "loc": "Green Park",
            "ward": "Ward 203",
            "zone": "South Zone",
            "lang": "hi",
            "summary": "ग्रीन पार्क में बड़ी झाड़ियों और घास की छंटाई का अनुरोध।"
        },
        {
            "id": "CMP-SYN-019",
            "time_offset_hrs": 19,
            "channel": "social_media",
            "text": "इंदिरा इंडस्ट्रियल एरिया ट्रांसपोर्ट नगर में भारी सड़क टूट गई है, बड़े ट्रकों के कारण गहरे गड्ढे हो गए हैं।",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "इंदिरा इंडस्ट्रियल एरिया",
            "dept": "DEPT_ROADS",
            "cat": "CAT_ROAD_DAMAGE",
            "subcat": "Surface erosion",
            "urgency": "MEDIUM",
            "score": 0.60,
            "reason": "Heavy vehicle route degradation: Significant carriageway rutting in freight zone.",
            "loc": "Indira Industrial Area",
            "ward": "Ward 202",
            "zone": "South Zone",
            "lang": "hi",
            "summary": "इंदिरा इंडस्ट्रियल एरिया में क्षतिग्रस्त सड़क एवं भारी गड्ढे।"
        },
        {
            "id": "CMP-SYN-020",
            "time_offset_hrs": 20,
            "channel": "state_helpline",
            "text": "वसंत विहार लेकव्यू कॉलोनी के पास बारिश का गंदा पानी भरा हुआ है। मच्छरों का भारी प्रकोप है, फॉगिंग कराई जाए।",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "वसंत विहार लेक व्यू",
            "dept": "DEPT_PUBLIC_HEALTH",
            "cat": "CAT_MOSQUITO_VECTOR_ISSUE",
            "subcat": "Anti-larval fogging request",
            "urgency": "HIGH",
            "score": 0.74,
            "reason": "Vector breeding threat: Stagnant rain pool generating heavy mosquito infestations.",
            "loc": "Vasant Vihar",
            "ward": "Ward 201",
            "zone": "South Zone",
            "lang": "hi",
            "summary": "वसंत विहार लेकव्यू के पास जलभराव और मच्छरों का प्रकोप, फॉगिंग की मांग।"
        },

        # --- HINGLISH COMPLAINTS ---
        {
            "id": "CMP-SYN-021",
            "time_offset_hrs": 21,
            "channel": "municipal_app",
            "text": "MPNagar zone 1 me Sargam ke paas bohot bada road pe gaddha ho gaya hai. Kal raat ek bike gir gayi thi please jaldi theek karo.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "MPNagar Sargam",
            "dept": "DEPT_ROADS",
            "cat": "CAT_POTHOLE",
            "subcat": "Deep carriageway crater",
            "urgency": "HIGH",
            "score": 0.83,
            "reason": "Repeated hazard incident: Crater in MP Nagar already caused bike fall.",
            "loc": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "MP Nagar Sargam cinema ke pass bada gaddha, bike accident hua."
        },
        {
            "id": "CMP-SYN-022",
            "time_offset_hrs": 22,
            "channel": "social_media",
            "text": "Shivaji nagar 6 number stop ke pass open manhole ka dhakkan gayab hai. Bacche school aate jate hain, risk hai.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/manhole_hinglish.jpg",
            "image_caption": "[SYNTHETIC_DEMO] School path ke bagal me khula hua gutter",
            "source_location": "Shivaji nagar 6 number stop",
            "dept": "DEPT_SEWERAGE",
            "cat": "CAT_OPEN_MANHOLE",
            "subcat": "Missing cover on main carriageway",
            "urgency": "CRITICAL",
            "score": 0.96,
            "reason": "Acute hazard trigger: Open manhole on primary school commute path.",
            "loc": "Shivaji Nagar",
            "ward": "Ward 101",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "Shivaji Nagar 6 number bus stop ke pass khula manhole bina dhakkan ke."
        },
        {
            "id": "CMP-SYN-023",
            "time_offset_hrs": 23,
            "channel": "state_helpline",
            "text": "Maharana Pratap Nagar me water pipeline toot gayi hai, pure road pe paani waste ho raha hai morning se.",
            "audio_path": "data/raw/synthetic/audio_leak_hinglish.mp3",
            "image_caption": None,
            "image_path": None,
            "source_location": "Maharana Pratap Nagar Coaching Hub",
            "dept": "DEPT_WATER",
            "cat": "CAT_WATER_LEAKAGE",
            "subcat": "Underground pipeline burst",
            "urgency": "HIGH",
            "score": 0.80,
            "reason": "Severe potable water loss: Pressurized line leakage flooding commercial hub.",
            "loc": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "Maharana Pratap Nagar me water pipeline leakage se sadak par paani bhara."
        },
        {
            "id": "CMP-SYN-024",
            "time_offset_hrs": 24,
            "channel": "elected_rep_message",
            "text": "Gandhi chowk clock tower market me 4 streetlights band padi hain, market me andhera rehta hai shaam ko.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Gandhi chowk clock tower",
            "dept": "DEPT_ELECTRICAL",
            "cat": "CAT_STREET_LIGHT_FAILURE",
            "subcat": "Single bulb fused",
            "urgency": "MEDIUM",
            "score": 0.60,
            "reason": "Commercial corridor darkness: Multiple non-functioning luminaire heads.",
            "loc": "Gandhi Chowk",
            "ward": "Ward 102",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "Gandhi Chowk Clock Tower me streetlights band hone se andhera."
        },
        {
            "id": "CMP-SYN-025",
            "time_offset_hrs": 25,
            "channel": "municipal_app",
            "text": "Vasant Kunj Extension me kachra uthane wali gaadi 4 din se nahi aayi, smell bohot kharab aa rahi hai.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Vasant Kunj Ext",
            "dept": "DEPT_SANITATION",
            "cat": "CAT_GARBAGE_COLLECTION",
            "subcat": "Door-to-door vehicle absent 3+ days",
            "urgency": "MEDIUM",
            "score": 0.55,
            "reason": "Waste accumulation: Sanitation truck missed residential colony for 4 consecutive days.",
            "loc": "Vasant Vihar",
            "ward": "Ward 201",
            "zone": "South Zone",
            "lang": "hi",
            "summary": "Vasant Kunj Extension me 4 din se garbage truck miss, kachra jama."
        },
        {
            "id": "CMP-SYN-026",
            "time_offset_hrs": 26,
            "channel": "state_helpline",
            "text": "Subhash nagar railway overbridge ke neeche construction material kisi ne road par dump kar diya hai, traffic jaam ho raha hai.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/debris_dump.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Sadak par gira mitti aur patthar ka dher",
            "source_location": "Subhash Nagar Overbridge",
            "dept": "DEPT_ROADS",
            "cat": "CAT_ROAD_OBSTRUCTION",
            "subcat": "Illegal construction material",
            "urgency": "MEDIUM",
            "score": 0.68,
            "reason": "Right of way obstruction: Dumped debris creating bottlenecks on busy road.",
            "loc": "Subhash Nagar",
            "ward": "Ward 302",
            "zone": "North Zone",
            "lang": "hi",
            "summary": "Subhash Nagar overbridge ke neeche illegal building material dump hone se traffic jam."
        },
        {
            "id": "CMP-SYN-027",
            "time_offset_hrs": 27,
            "channel": "social_media",
            "text": "Railway colony Loco Shed ke paas transformer se spark nikal rahi hai. Bada accident ho sakta hai please send electrical team urgently.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/sparking_transformer.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Bijli ke khambhe ke upar se nikalte shole",
            "source_location": "Railway Colony Loco Shed",
            "dept": "DEPT_ELECTRICAL",
            "cat": "CAT_DAMAGED_ELECTRICAL_POLE",
            "subcat": "Sparking overhead line",
            "urgency": "CRITICAL",
            "score": 0.99,
            "reason": "Mandatory safety rule trigger: Active electrical sparks from utility transformer.",
            "loc": "Railway Colony",
            "ward": "Ward 104",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "Railway colony Loco Shed ke paas transformer me continuous sparking, immediate danger."
        },
        {
            "id": "CMP-SYN-028",
            "time_offset_hrs": 28,
            "channel": "municipal_app",
            "text": "Civil lines officers colony park me bench tooti hui hai aur paani ka fountain kharab hai.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Civil Lines Officers Colony",
            "dept": "DEPT_PARKS",
            "cat": "CAT_BROKEN_PARK_EQUIPMENT",
            "subcat": "Damaged concrete park bench",
            "urgency": "LOW",
            "score": 0.28,
            "reason": "Amenity maintenance: Non-urgent park infrastructure repair request.",
            "loc": "Civil Lines",
            "ward": "Ward 301",
            "zone": "North Zone",
            "lang": "hi",
            "summary": "Civil lines park me broken bench aur non-functional fountain."
        },
        {
            "id": "CMP-SYN-029",
            "time_offset_hrs": 29,
            "channel": "state_helpline",
            "text": "Indira industrial estate truck stand ke pass naali poori block hai aur foul smell aa rahi hai.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Indira industrial truck stand",
            "dept": "DEPT_SEWERAGE",
            "cat": "CAT_SEWER_BLOCKAGE",
            "subcat": "Underground line blocked",
            "urgency": "MEDIUM",
            "score": 0.65,
            "reason": "Clogged industrial drain: Severe stagnant sewage odor near transport terminal.",
            "loc": "Indira Industrial Area",
            "ward": "Ward 202",
            "zone": "South Zone",
            "lang": "hi",
            "summary": "Indira Industrial Area truck stand ke pass blocked sewer drain."
        },
        {
            "id": "CMP-SYN-030",
            "time_offset_hrs": 30,
            "channel": "elected_rep_message",
            "text": "Nehru market chowk par stray dogs bohot badh gaye hain aur logo ko kaat rahe hain, public health team bhejiye.",
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "Nehru Chowk Market",
            "dept": "DEPT_PUBLIC_HEALTH",
            "cat": "CAT_SANITATION_HAZARD",
            "subcat": "Stagnant green cesspool",
            "urgency": "HIGH",
            "score": 0.82,
            "reason": "Canine menace hazard: Aggressive animal pack reports near public bazaar.",
            "loc": "Nehru Market",
            "ward": "Ward 103",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "Nehru Market me stray dogs ka aatank, immediate intervention required."
        },
        {
            "id": "CMP-SYN-031",
            "time_offset_hrs": 31,
            "channel": "social_media",
            "text": "Green Park botanical garden jogging track pe bada tree branch gir gaya hai, walk path poora block hai.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/fallen_branch.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Jogging track par gira hua ped ki moti shaakh",
            "source_location": "Green Park Botanical Garden",
            "dept": "DEPT_PARKS",
            "cat": "CAT_PARK_MAINTENANCE",
            "subcat": "Hazardous hanging tree limb",
            "urgency": "MEDIUM",
            "score": 0.58,
            "reason": "Pedestrian obstruction: Fallen bough blocking morning running track in park.",
            "loc": "Green Park",
            "ward": "Ward 203",
            "zone": "South Zone",
            "lang": "hi",
            "summary": "Green Park jogging track par tree branch girne se path block."
        },
        {
            "id": "CMP-SYN-032",
            "time_offset_hrs": 32,
            "channel": "municipal_app",
            "text": "Shivaji Nagar sector A me municipal tap se ganda peela paani aa raha hai, typhoid ka khatra hai.",
            "audio_path": None,
            "image_path": "data/raw/synthetic/yellow_water.jpg",
            "image_caption": "[SYNTHETIC_DEMO] Glass me bhara peela matmela paani",
            "source_location": "Shivaji Nagar Sector A",
            "dept": "DEPT_WATER",
            "cat": "CAT_WATER_QUALITY",
            "subcat": "Sewage mixed with drinking water",
            "urgency": "CRITICAL",
            "score": 0.95,
            "reason": "Epidemic hazard: Suspected sewage infiltration into drinking lines in high-density colony.",
            "loc": "Shivaji Nagar",
            "ward": "Ward 101",
            "zone": "Central Zone",
            "lang": "hi",
            "summary": "Shivaji Nagar Sector A me contaminated yellow tap water, health hazard."
        }
    ]

    # Create Duplicate Cluster 1: The MP Nagar Pothole cluster (CMP-SYN-001, CMP-SYN-013, CMP-SYN-021)
    cluster_1 = DuplicateCluster(
        cluster_id="CLUST-MPNAGAR-POTHOLE-01",
        summary="Major dangerous carriageway crater near Sargam Cinema, MP Nagar causing vehicle skidding.",
        confidence=0.94,
        detection_method="spatial_temporal_semantic",
        is_active=True,
        created_at=base_time + timedelta(hours=22)
    )
    db.add(cluster_1)

    # Create Duplicate Cluster 2: The Shivaji Nagar Water Quality crisis (CMP-SYN-003, CMP-SYN-032)
    cluster_2 = DuplicateCluster(
        cluster_id="CLUST-SHIVAJI-WATER-02",
        summary="Water supply infrastructure breakdown & contaminated water reported across Shivaji Nagar Sector A.",
        confidence=0.88,
        detection_method="spatial_temporal_semantic",
        is_active=True,
        created_at=base_time + timedelta(hours=32)
    )
    db.add(cluster_2)
    db.flush()

    for item in raw_data:
        complaint_time = base_time + timedelta(hours=item["time_offset_hrs"])

        # 1. Insert immutable RawComplaint
        raw = RawComplaint(
            complaint_id=item["id"],
            timestamp=complaint_time,
            channel=item["channel"],
            text=item["text"],
            audio_path=item["audio_path"],
            image_path=item["image_path"],
            image_caption=item["image_caption"],
            source_location=item["source_location"],
            department_label=item["dept"],
            category_label=item["cat"],
            urgency_label=item["urgency"],
            created_at=complaint_time
        )
        db.add(raw)
        db.flush()

        # Check cluster affiliation
        assigned_cluster_id = None
        cluster_conf = None
        if item["id"] in ["CMP-SYN-001", "CMP-SYN-013", "CMP-SYN-021"]:
            assigned_cluster_id = "CLUST-MPNAGAR-POTHOLE-01"
            cluster_conf = 0.92
            db.add(ClusterMember(
                cluster_id=assigned_cluster_id,
                complaint_id=item["id"],
                similarity_score=0.92,
                added_at=complaint_time
            ))
        elif item["id"] in ["CMP-SYN-003", "CMP-SYN-032"]:
            assigned_cluster_id = "CLUST-SHIVAJI-WATER-02"
            cluster_conf = 0.89
            db.add(ClusterMember(
                cluster_id=assigned_cluster_id,
                complaint_id=item["id"],
                similarity_score=0.89,
                added_at=complaint_time
            ))

        # 2. Insert Acknowledgement draft
        ack_status = "draft"
        approved_at = None
        approved_by = None
        edited_at = None

        if item["id"] in ["CMP-SYN-001", "CMP-SYN-002", "CMP-SYN-011"]:
            ack_status = "approved"
            approved_at = complaint_time + timedelta(minutes=45)
            approved_by = "OPERATOR_DESK_42"
        elif item["id"] in ["CMP-SYN-003", "CMP-SYN-012"]:
            ack_status = "edited"
            edited_at = complaint_time + timedelta(minutes=20)

        ack = Acknowledgement(
            complaint_id=item["id"],
            draft_text=f"Dear Citizen, your complaint (ID: {item['id']}) regarding {item['summary']} has been registered with {item['dept']} for Ward {item['ward']}.",
            language=item["lang"],
            status=ack_status,
            generated_at=complaint_time + timedelta(minutes=5),
            edited_at=edited_at,
            approved_at=approved_at,
            approved_by=approved_by
        )
        db.add(ack)
        db.flush()

        # 3. Insert TriagedComplaint
        proc_status = "OPERATOR_REVIEW_PENDING"
        if ack_status == "approved":
            proc_status = "OPERATOR_APPROVED"

        triaged = TriagedComplaint(
            complaint_id=item["id"],
            language=item["lang"],
            summary=item["summary"],
            department=item["dept"],
            category=item["cat"],
            subcategory=item["subcat"],
            urgency=item["urgency"],
            urgency_score=item["score"],
            urgency_reason=item["reason"],
            normalized_locality=item["loc"],
            ward=item["ward"],
            zone=item["zone"],
            duplicate_cluster_id=assigned_cluster_id,
            duplicate_confidence=cluster_conf,
            routing_evidence=f"Matched keywords from '{item['text'][:40]}...' into {item['dept']} / {item['cat']}",
            routing_confidence=0.91,
            acknowledgement_id=ack.id,
            processing_status=proc_status,
            model_version="gemini-2.5-flash-triage-v1",
            prompt_version="prompt-v1.0",
            processed_at=complaint_time + timedelta(minutes=5)
        )
        db.add(triaged)

        # 4. Insert Initial StatusHistory
        db.add(StatusHistory(
            complaint_id=item["id"],
            old_status=None,
            new_status="RAW",
            changed_by="system_ingestion",
            timestamp=complaint_time,
            notes="Ingested raw export record from channel."
        ))
        db.add(StatusHistory(
            complaint_id=item["id"],
            old_status="RAW",
            new_status=proc_status,
            changed_by="ai_triage_engine" if proc_status == "OPERATOR_REVIEW_PENDING" else "operator_desk_42",
            timestamp=complaint_time + timedelta(minutes=5),
            notes=f"Triage processed with urgency {item['urgency']} (score {item['score']})."
        ))

    db.commit()


def seed_weekly_reports_and_evaluation(db):
    if db.query(WeeklyReport).first():
        print("Weekly reports and evaluation results already seeded. Skipping.")
        return

    print("Seeding sample weekly report and evaluation result...")
    # Seed Weekly Report
    today = date.today()
    start_date = today - timedelta(days=7)

    report_swm = WeeklyReport(
        report_period_start=start_date,
        report_period_end=today,
        department="Solid Waste Management",
        complaints_received=45,
        complaints_resolved=38,
        complaints_pending=7,
        median_resolution_time=14.2,
        repeat_complaints=6,
        top_categories=[
            {"category": "Garbage Collection", "count": 25},
            {"category": "Garbage Dump", "count": 14},
            {"category": "Sanitation Issue", "count": 6}
        ],
        major_clusters=[
            {"cluster_id": "CLUST-MPNAGAR-POTHOLE-01", "locality": "MP Nagar", "reports": 3}
        ],
        generated_at=datetime.now(timezone.utc)
    )
    db.add(report_swm)

    # Seed Sample Evaluation Result
    eval_result = EvaluationResult(
        test_set_version="heldout_test_v1.0",
        total_samples=120,
        department_accuracy=0.916,
        category_accuracy=0.875,
        urgency_accuracy=0.900,
        locality_normalization_accuracy=0.933,
        duplicate_reduction=24.5,
        confusion_matrix={
            "DEPT_ROADS": {"correct": 28, "total": 30},
            "DEPT_WATER": {"correct": 23, "total": 25},
            "DEPT_SEWERAGE": {"correct": 19, "total": 20},
            "DEPT_ELECTRICAL": {"correct": 20, "total": 22},
            "DEPT_SANITATION": {"correct": 20, "total": 23}
        },
        per_class_metrics={
            "precision_macro": 0.902,
            "recall_macro": 0.898,
            "f1_macro": 0.900
        },
        is_synthetic_benchmark=True,
        evaluated_at=datetime.now(timezone.utc),
        notes="[SYNTHETIC_BENCHMARK] Baseline pipeline run against synthetic held-out validation batch."
    )
    db.add(eval_result)
    db.commit()


def run_seed():
    print("=" * 60)
    print("Starting NagarSetu Phase 2 Database Seeding")
    print("=" * 60)
    create_tables()
    db = SessionLocal()
    try:
        dept_map = seed_departments(db)
        seed_categories(db, dept_map)
        seed_gazetteer(db)
        seed_synthetic_complaints(db)
        seed_weekly_reports_and_evaluation(db)
        print("=" * 60)
        print("Database Seeding Completed Successfully!")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
