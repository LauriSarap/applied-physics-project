import csv, json, math

ROWS, COLS = 16, 15
MAX_EVENTS = 50
DETECTOR_LEVELS = [1, 2, 3]
TAKE_ALL_EVENTS = False

TIME_COL = 0
X_COL = 1
Y_COL = 2
DETECTOR_COL = 7

xmin = ymin = math.inf
xmax = ymax = -math.inf

# X-Y vahemiku arvutamine
# Skaleerime kogu 1x2 m meie 16x15 ruudustikule
with open("gscan_example_data.csv", newline="", encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        try:    
            detector = int(row[DETECTOR_COL])
            if detector != 1:
                continue
                
            x = float(row[X_COL])
            y = float(row[Y_COL])
                
            xmin, xmax = min(xmin, x), max(xmax, x)
            ymin, ymax = min(ymin, y), max(ymax, y)
        except (IndexError, ValueError) as e:
            continue
                
print(f"Full dataset range: X: {xmin} to {xmax}, Y: {ymin} to {ymax}")

# Kahe vektroi vaheline nurk koosinuse abil
def calculate_angle_2d(p1, p2, p3):
    v1 = [p2[0] - p1[0], p2[1] - p1[1]]
    v2 = [p3[0] - p2[0], p3[1] - p2[1]]
    
    dot_product = v1[0]*v2[0] + v1[1]*v2[1]
    
    mag_v1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag_v2 = math.sqrt(v2[0]**2 + v2[1]**2)
    
    if mag_v1 < 1e-10 or mag_v2 < 1e-10:
        return 0.0
    
    cos_angle = dot_product / (mag_v1 * mag_v2)
    cos_angle = max(min(cos_angle, 1.0), -1.0)
    
    return math.acos(cos_angle)

# Diskreetsed osakeste jaotused hajumisnurga järgi
# Värvid vastavad (vahemik on 0-pi radiaani ehk 0-180 kraadi)
# 0 - 0.06 -> sinine
# 0.06 - 0.12 -> punane
# 0.12 - edasi -> jätame andmestikust välja
def angle_to_rgb(angle):
    if angle < 0.06:
        return [0, 0, 255]
    elif angle < 0.12:
        return [255, 0, 0]
    else:
        return None

events_by_time = {}
first_timestamp = None

with open("gscan_example_data.csv", newline="", encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        try:
            detector = int(row[DETECTOR_COL])
            if detector not in DETECTOR_LEVELS:
                continue
                
            t_ns = float(row[TIME_COL])
            
            if first_timestamp is None:
                first_timestamp = t_ns
                
            x = float(row[X_COL])
            y = float(row[Y_COL])
            
            if t_ns not in events_by_time:
                events_by_time[t_ns] = {}
                
            events_by_time[t_ns][detector] = [x, y]
                
        except (IndexError, ValueError) as e:
            continue

hits = []
event_count = 0
angles = []

for t_ns in events_by_time:
    event = events_by_time[t_ns]
    
    if not all(level in event for level in DETECTOR_LEVELS):
        continue
    
    pos1 = event[1]
    pos2 = event[2]
    pos3 = event[3]
    
    angle = calculate_angle_2d(pos1, pos2, pos3)
    
    # Jätame välja osakese, mille hajumisnurk > 0.12 radiaani
    if angle > 0.12:
        continue
    
    angles.append(angle)
    
    rgb = angle_to_rgb(angle)
    
    x, y = pos1[0], pos1[1]
    
    t_sec = (t_ns - first_timestamp) / 1e9
    
    col = round((x - xmin) / (xmax - xmin) * (COLS - 1))
    row = round((y - ymin) / (ymax - ymin) * (ROWS - 1))
    
    hits.append([t_sec, row, col, rgb])
    
    event_count += 1
    if event_count >= MAX_EVENTS and not TAKE_ALL_EVENTS:
        break

if hits:
    with open("hits.json", "w") as out:
        json.dump(hits, out)

    if hits:
        print(f"Particles with angles > 0.12 radians are excluded from the dataset")
        print(f"Angle range: {min(angles):.4f} to {max(angles):.4f} radians")
        print(f"Color mapping: 0-0.06 radians -> blue, 0.06-0.12 radians -> red")
    if not TAKE_ALL_EVENTS:
        print(f"(Limited to first {MAX_EVENTS} complete events)")
    else:
        print(f"Processed all {event_count} complete events")
else:
    print(f"No events found with all required detector levels: {DETECTOR_LEVELS}")