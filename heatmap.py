import json
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D
import time

# Grid dimensions
ROWS, COLS = 16, 15
DELAY_MODE_INTERVAL = 3.0  # seconds between hits in delay mode

def load_hits_data(filename="hits.json"):
    try:
        with open(filename, 'r') as f:
            hits = json.load(f)
        print(f"Loaded {len(hits)} hits from {filename}")
        return hits
    except FileNotFoundError:
        print(f"Error: {filename} not found. Please run preprocess.py first.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filename}")
        return []

def create_heatmap_data(hits):
    heatmap_grid = np.zeros((ROWS, COLS))
    
    for hit in hits:
        time, row, col, rgb = hit
        if 0 <= row < ROWS and 0 <= col < COLS:
            heatmap_grid[row][col] += 1
    
    return heatmap_grid

def save_heatmap_visualization(heatmap_grid):
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    fig.suptitle('Detector Hit Analysis', fontsize=16, fontweight='bold')
    
    im = ax.imshow(heatmap_grid, cmap='hot', interpolation='nearest')
    ax.set_title('Hit Frequency Heatmap')
    ax.set_xlabel('Column')
    ax.set_ylabel('Row')
    plt.colorbar(im, ax=ax, label='Number of Hits')
    
    for i in range(ROWS):
        for j in range(COLS):
            if heatmap_grid[i, j] > 0:
                ax.text(j, i, f'{int(heatmap_grid[i, j])}', 
                        ha="center", va="center", color="white", fontsize=8)
    
    plt.tight_layout()
    plt.savefig('heatmap_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved heatmap visualization as 'heatmap_analysis.png'")
    plt.close()

def print_statistics(heatmap_grid, hits):
    total_hits = len(hits)
    active_cells = np.count_nonzero(heatmap_grid)
    max_hits = int(np.max(heatmap_grid))
    avg_hits = np.mean(heatmap_grid[heatmap_grid > 0]) if active_cells > 0 else 0
    
    print(f"\n=== Heatmap Statistics ===")
    print(f"Total hits: {total_hits}")
    print(f"Grid size: {ROWS}x{COLS} = {ROWS * COLS} cells")
    print(f"Active cells (with hits): {active_cells}")
    print(f"Max hits in single cell: {max_hits}")
    print(f"Average hits per active cell: {avg_hits:.2f}")

class RealTimeHeatmap3D:
    def __init__(self, hits, use_real_time=True):
        self.hits = hits
        self.use_real_time = use_real_time
        self.current_grid = np.zeros((ROWS, COLS))
        self.hit_index = 0
        self.start_time = time.time()
        self.first_hit_time = hits[0][0] if hits else 0
        
        self.fig = plt.figure(figsize=(12, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        self.x_pos, self.y_pos = np.meshgrid(range(COLS), range(ROWS))
        self.x_pos = self.x_pos.flatten()
        self.y_pos = self.y_pos.flatten()
        
        self.bars = None
        self.setup_plot()
        
    def setup_plot(self):
        self.ax.set_xlabel('Column')
        self.ax.set_ylabel('Row')
        self.ax.set_zlabel('Hits')  # type: ignore
        self.ax.set_title('Real-time 3D Heatmap')
        self.ax.set_xlim(0, COLS-1)
        self.ax.set_ylim(0, ROWS-1)
        
    def update_plot(self, frame):
        if self.hit_index >= len(self.hits):
            return []
            
        current_time = time.time() - self.start_time
        
        if self.use_real_time:
            hit_time = self.hits[self.hit_index][0] - self.first_hit_time
            if current_time < hit_time:
                return []
        else:
            expected_time = self.hit_index * DELAY_MODE_INTERVAL
            if current_time < expected_time:
                return []
        
        while self.hit_index < len(self.hits):
            hit = self.hits[self.hit_index]
            hit_time, row, col, rgb = hit
            
            if self.use_real_time:
                if hit_time - self.first_hit_time > current_time:
                    break
            else:
                if self.hit_index * DELAY_MODE_INTERVAL > current_time:
                    break
                    
            if 0 <= row < ROWS and 0 <= col < COLS:
                self.current_grid[row][col] += 1
            
            self.hit_index += 1
        
        self.ax.clear()
        self.setup_plot()
        
        heights = self.current_grid.flatten()
        max_val = np.max(heights)
        colors = plt.cm.hot(heights / (max_val + 1e-10))  # type: ignore
        
        self.bars = self.ax.bar3d(self.x_pos, self.y_pos, np.zeros_like(heights),  # type: ignore
                                 0.8, 0.8, heights, color=colors, alpha=0.8)
        
        max_height = max_val if max_val > 0 else 1
        self.ax.set_zlim(0, max_height * 1.1)  # type: ignore
        
        progress = (self.hit_index / len(self.hits)) * 100
        mode_text = "Real-time" if self.use_real_time else f"Delay ({DELAY_MODE_INTERVAL}s)"
        self.ax.text2D(0.02, 0.98, f"Mode: {mode_text}\nProgress: {progress:.1f}%\nHits: {self.hit_index}/{len(self.hits)}",  # type: ignore
                      transform=self.ax.transAxes, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        return []
        
    def start_animation(self):
        self.ani = animation.FuncAnimation(self.fig, self.update_plot, interval=50, blit=False)
        plt.show()

def main():
    print("=== Heatmap Generator ===")
    
    hits = load_hits_data()
    if not hits:
        return
    
    print("Creating static heatmap...")
    heatmap_grid = create_heatmap_data(hits)
    print_statistics(heatmap_grid, hits)
    save_heatmap_visualization(heatmap_grid)
    
    print("\nChoose 3D visualization mode:")
    print("1. Real-time (using actual time data)")
    print("2. Delay mode (configurable interval)")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter 1 or 2")
    
    use_real_time = choice == '1'
    
    if not use_real_time:
        try:
            global DELAY_MODE_INTERVAL
            interval = float(input(f"Enter delay between hits in seconds (default {DELAY_MODE_INTERVAL}): ") or DELAY_MODE_INTERVAL)
            DELAY_MODE_INTERVAL = max(0.1, interval)
        except ValueError:
            print(f"Using default interval: {DELAY_MODE_INTERVAL}s")
    
    print(f"\nStarting 3D visualization...")
    print("Close the window to exit.")
    
    heatmap_3d = RealTimeHeatmap3D(hits, use_real_time)
    heatmap_3d.start_animation()

if __name__ == "__main__":
    main()
