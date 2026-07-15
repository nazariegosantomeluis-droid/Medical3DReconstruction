from src.io.load_volume import load_volume
from src.analysis.volume_info import print_volume_info
from src.visualization.show_slice import show_middle_slice

def main():

    print("=" * 40)
    print("Medical 3D Reconstruction")
    print("=" * 40)

    print("\nLoading volume...\n")

    volume = load_volume("data/volumes/CTChest.nrrd")

    print("Volume loaded successfully!")

    print_volume_info(volume)

    show_middle_slice(volume)
    
if __name__ == "__main__":
    main()