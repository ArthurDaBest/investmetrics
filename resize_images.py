from PIL import Image
import os

def resize_image(input_path, output_path, size=(300, 300)):
    with Image.open(input_path) as img:
        img = img.resize(size, Image.LANCZOS)
        img.save(output_path)

def main():
    input_folder = 'app/static/assets/img/team'
    output_folder = 'app/static/assets/img/team/resized'
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for filename in os.listdir(input_folder):
        if filename.endswith(('.jpg', '.jpeg', '.png', '.JPG')):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            resize_image(input_path, output_path)
            print(f"Resized {filename}")

if __name__ == "__main__":
    main()
