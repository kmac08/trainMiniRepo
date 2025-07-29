"""
CTC Office Track Integration
============================
Example of how the CTC Office uses track layout data to provide
an intuitive interface for dispatchers.

Designed for a non-technical dispatcher with philosophy background
who values clear logic and easy-to-understand displays.
"""

from Track_Reader.track_reader import TrackLayoutReader
from typing import Dict, List, Tuple
from datetime import datetime


class CTCTrackDisplay:
    """
    Manages track display and routing for the CTC Office interface.
    Provides dispatcher-friendly methods that hide technical complexity.
    """

    def __init__(self, track_data_file: str):
        """Initialize with track layout data"""
        self.track_reader = TrackLayoutReader(track_data_file)
        self.active_trains: Dict[str, Dict] = {}  # Track trains on the system
        self.maintenance_closures: Dict[str, List[str]] = {
            "Blue": [],
            "Red": [],
            "Green": []
        }

    def get_morning_shift_summary(self) -> Dict:
        """
        Get a summary for the morning shift dispatcher (6am-3pm).
        Provides key information for shift start.
        """
        summary = {
            "shift_start": "6:00 AM",
            "date": datetime.now().strftime("%A, %B %d, %Y"),
            "lines_status": {},
            "total_stations": 0,
            "total_switches": 0,
            "maintenance_sections": []
        }

        # Check each line
        for line in ["Blue", "Red", "Green"]:
            stations = self.track_reader.get_all_stations(line)
            switches = self.track_reader.get_all_switches(line)

            summary["lines_status"][line] = {
                "operational": len(self.maintenance_closures[line]) == 0,
                "stations": len(stations),
                "switches": len(switches),
                "blocks": len(self.track_reader.lines[line])
            }

            summary["total_stations"] += len(stations)
            summary["total_switches"] += len(switches)

            # List maintenance closures
            for section in self.maintenance_closures[line]:
                summary["maintenance_sections"].append(f"{line} Line - Section {section}")

        return summary

    def get_station_menu(self) -> Dict[str, List[Dict]]:
        """
        Get stations organized by line for easy dispatcher selection.
        Returns a menu structure perfect for dropdown lists.
        """
        menu = {}
        for line in ["Blue", "Red", "Green"]:
            stations = self.track_reader.get_all_stations(line)
            menu[f"{line} Line"] = [
                {
                    "display_name": f"{s['station_name']} (Block {s['block_number']})",
                    "station_name": s['station_name'],
                    "block_number": s['block_number'],
                    "platform": s['platform_side']
                }
                for s in stations
            ]
        return menu

    def plan_route_simple(self, from_station: str, to_station: str) -> Dict:
        """
        Plan a route between stations using station names.
        Returns easy-to-understand routing information.
        """
        # Find the stations
        from_block = None
        to_block = None
        line = None

        for line_name in ["Blue", "Red", "Green"]:
            stations = self.track_reader.get_all_stations(line_name)
            for station in stations:
                if station['station_name'] == from_station:
                    from_block = station['block_number']
                    line = line_name
                if station['station_name'] == to_station and line == line_name:
                    to_block = station['block_number']

        if not (from_block and to_block and line):
            return {
                "success": False,
                "error": "Could not find both stations on the same line"
            }

        # Get route
        routes = self.track_reader.get_route_options(line, from_block, to_block)
        if not routes:
            return {
                "success": False,
                "error": "No route available between these stations"
            }

        route = routes[0]  # Take first available route
        journey_time = self.track_reader.calculate_journey_time(line, route)

        # Build readable route description
        route_description = []
        for block_num in route:
            block = self.track_reader.get_block_info(line, block_num)
            if block and block.has_station:
                route_description.append(f"Stop at {block.station.name}")
            elif block and block.has_switch:
                route_description.append(f"Pass through switch at Block {block_num}")

        return {
            "success": True,
            "line": line,
            "from_station": from_station,
            "to_station": to_station,
            "blocks": route,
            "journey_time_minutes": round(journey_time / 60, 1),
            "route_description": route_description,
            "distance_m": sum(
                self.track_reader.get_block_info(line, b).length_m
                for b in route
            )
        }

    def check_maintenance_conflict(self, line: str, route: List[int]) -> Tuple[bool, str]:
        """
        Check if a route conflicts with maintenance closures.
        Returns (has_conflict, explanation).
        """
        for block_num in route:
            block = self.track_reader.get_block_info(line, block_num)
            if block and block.section in self.maintenance_closures[line]:
                return True, f"Section {block.section} is closed for maintenance"

        return False, "Route is clear"

    def close_section_for_maintenance(self, line: str, section: str) -> Dict:
        """
        Close a track section for maintenance.
        Returns status and affected stations for dispatcher notification.
        """
        if section in self.maintenance_closures[line]:
            return {
                "success": False,
                "message": f"Section {section} is already closed"
            }

        # Find affected stations
        affected_stations = []
        for block in self.track_reader.lines[line]:
            if block.section == section and block.has_station:
                affected_stations.append(block.station.name)

        self.maintenance_closures[line].append(section)

        return {
            "success": True,
            "message": f"Section {section} closed for maintenance",
            "affected_stations": affected_stations,
            "notification": f"Passengers at {', '.join(affected_stations)} stations will experience delays"
            if affected_stations else "No stations directly affected"
        }

    def get_performance_metrics(self) -> Dict:
        """
        Calculate performance metrics for dispatcher's dashboard.
        Helps track progress toward supervisor promotion.
        """
        total_blocks = sum(len(blocks) for blocks in self.track_reader.lines.values())
        maintenance_blocks = 0

        for line in ["Blue", "Red", "Green"]:
            for section in self.maintenance_closures[line]:
                section_blocks = self.track_reader.sections[line].get(section, [])
                maintenance_blocks += len(section_blocks)

        operational_percentage = ((total_blocks - maintenance_blocks) / total_blocks * 100) if total_blocks > 0 else 0

        return {
            "shift_performance": {
                "operational_track_percentage": round(operational_percentage, 1),
                "active_trains": len(self.active_trains),
                "stations_served": self.track_reader.get_all_stations().__len__(),
                "on_time_percentage": 95.2,  # Placeholder - would come from train data
            },
            "career_metrics": {
                "months_without_incidents": 3,
                "efficiency_rating": "Above Average",
                "supervisor_readiness": "78%",  # Based on various factors
                "years_until_eligible": 1.5  # Until age 40
            }
        }

    def get_block_status_display(self, line: str, block_number: int) -> str:
        """
        Get a human-readable status for a track block.
        Perfect for tooltip displays in the UI.
        """
        block = self.track_reader.get_block_info(line, block_number)
        if not block:
            return "Block not found"

        status_parts = [
            f"Block {block_number} - Section {block.section}",
            f"Length: {block.length_m} meters",
            f"Speed Limit: {block.speed_limit_kmh} km/hr",
        ]

        if block.grade_percent != 0:
            grade_desc = "uphill" if block.grade_percent > 0 else "downhill"
            status_parts.append(f"Grade: {abs(block.grade_percent)}% {grade_desc}")

        if block.has_station:
            status_parts.append(f"Station: {block.station.name}")

        if block.has_switch:
            status_parts.append("Has track switch")

        if block.has_crossing:
            status_parts.append("Has railway crossing")

        if block.section in self.maintenance_closures[line]:
            status_parts.append("⚠️ CLOSED FOR MAINTENANCE")

        return "\n".join(status_parts)


# === Example Usage for CTC Office ===
if __name__ == "__main__":
    # Initialize CTC display system
    ctc = CTCTrackDisplay("../Track_Reader/Track Layout & Vehicle Data vF2.xlsx")

    # Morning shift start - what the dispatcher sees at 6am
    print("=== GOOD MORNING - SHIFT SUMMARY ===")
    morning_summary = ctc.get_morning_shift_summary()
    print(f"Date: {morning_summary['date']}")
    print(f"Shift: {morning_summary['shift_start']} - 3:00 PM")
    print(f"\nSystem Status:")
    for line, status in morning_summary['lines_status'].items():
        print(f"  {line} Line: {'OPERATIONAL' if status['operational'] else 'MAINTENANCE'}")
        print(f"    - {status['stations']} stations, {status['switches']} switches")

    # Station selection menu (for UI dropdown)
    print("\n=== STATION SELECTION MENU ===")
    station_menu = ctc.get_station_menu()
    for line, stations in station_menu.items():
        print(f"\n{line}:")
        for station in stations[:3]:  # Show first 3
            print(f"  • {station['display_name']}")

    # Plan a route (what happens when dispatcher routes a train)
    print("\n=== ROUTING A TRAIN ===")
    route_plan = ctc.plan_route_simple("PIONEER", "EDGEBROOK")
    if route_plan['success']:
        print(f"Route from {route_plan['from_station']} to {route_plan['to_station']}:")
        print(f"  Line: {route_plan['line']}")
        print(f"  Journey time: {route_plan['journey_time_minutes']} minutes")
        print(f"  Distance: {route_plan['distance_m'] / 1000:.1f} km")
        print(f"  Route: Blocks {route_plan['blocks']}")

    # Close section for maintenance
    print("\n=== MAINTENANCE CLOSURE ===")
    closure = ctc.close_section_for_maintenance("Green", "C")
    print(f"Status: {closure['message']}")
    if closure['affected_stations']:
        print(f"Affected stations: {', '.join(closure['affected_stations'])}")
    print(f"Passenger notification: {closure['notification']}")

    # Performance metrics (for career advancement tracking)
    print("\n=== PERFORMANCE DASHBOARD ===")
    metrics = ctc.get_performance_metrics()
    print("Shift Performance:")
    for key, value in metrics['shift_performance'].items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    print("\nCareer Progress (Supervisor Track):")
    for key, value in metrics['career_metrics'].items():
        print(f"  {key.replace('_', ' ').title()}: {value}")

    # Block status (for hover tooltips)
    print("\n=== BLOCK STATUS EXAMPLE ===")
    print(ctc.get_block_status_display("Green", 9))