#!/usr/bin/env python3
#this is just a reference tool for testing station numbers and names

"""
Station Number Reference Tool
Shows all stations with their numbers, names, blocks, and platform sides for testing
"""

import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'Track_Reader_new'))

try:
    from track_reader import TrackLayoutReader
    
    def show_all_stations(line_name=None):
        """Show all stations with their numbers for easy testing reference"""
        print("=" * 80)
        print("STATION NUMBER REFERENCE FOR TESTING")
        print("=" * 80)
        
        try:
            # Load track data
            excel_path = os.path.join(os.path.dirname(__file__), 'Track_Reader_new', 'Track Layout & Vehicle Data vF2.xlsx')
            
            if not os.path.exists(excel_path):
                print(f"ERROR: Excel file not found at {excel_path}")
                return
            
            lines_to_check = [line_name] if line_name else ['Red', 'Green']
            
            for line in lines_to_check:
                print(f"\n=== {line.upper()} LINE STATIONS ===")
                
                try:
                    reader = TrackLayoutReader(excel_path, selected_lines=[line])
                    stations = reader.get_stations_on_line(line)
                    
                    if not stations:
                        print(f"No stations found on {line} line")
                        continue
                    
                    print(f"Found {len(stations)} stations:")
                    print("-" * 60)
                    print(f"{'Num':<4} | {'Block':<6} | {'Platform':<8} | {'Station Name':<30}")
                    print("-" * 60)
                    
                    for station in stations:
                        station_num = station['station_id']
                        block_num = station['block_number']
                        platform = station['platform_side']
                        name = station['name']
                        
                        print(f"{station_num:<4} | {block_num:<6} | {platform:<8} | {name:<30}")
                    
                    print("-" * 60)
                    print(f"To test: Set 'Next Station Number' in Train Model UI to any number from 1-{len(stations)}")
                    
                except Exception as e:
                    print(f"Error loading {line} line: {e}")
            
            print("\n" + "=" * 80)
            print("TESTING INSTRUCTIONS:")
            print("1. Run main_test.py")
            print("2. In Train Model Test Bench, set 'Next Station Number' to any number above")
            print("3. Click 'SAVE AND SEND' to apply")
            print("4. Check Driver UI to see the station name and platform side appear")
            print("5. Stop the train (authority = 0) to see doors open on correct side")
            print("=" * 80)
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    if __name__ == "__main__":
        # Check if specific line requested
        line = sys.argv[1] if len(sys.argv) > 1 else None
        if line and line.lower() not in ['red', 'green']:
            print("Usage: python show_stations.py [red|green]")
            sys.exit(1)
        
        show_all_stations(line.title() if line else None)

except ImportError as e:
    print(f"ERROR: Cannot import track reader: {e}")
    print("Make sure pandas and openpyxl are installed:")
    print("pip install pandas openpyxl")