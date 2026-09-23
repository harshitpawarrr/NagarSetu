# Municipal Gazetteer (Zone, Ward, Locality & Landmark Directory)

The gazetteer provides deterministic spatial reference mappings for civic complaint triage.

## Purpose
Raw complaints contain colloquial locality descriptions, landmark mentions, and informal colony names (e.g., "near water tank behind Sharma market"). The gazetteer enables the locality normalization pipeline to deterministically resolve colloquial text to an official municipal:
- **Zone** (e.g., North Zone, South Zone, Central Zone)
- **Ward Number / Name** (e.g., Ward 14 - Shivaji Nagar)
- **Official Locality / Sub-locality**
- **Known Landmarks** (hospitals, schools, metro stations, markets)

## Format
JSON data structure containing zones, wards, aliases, landmarks, and geographic boundaries.
See `sample_wards_gazetteer.json` for the reference schema.
