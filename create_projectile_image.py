from PIL import Image
import os

print("投擲用の石の画像を生成します...")
assets_path = 'assets'
os.makedirs(assets_path, exist_ok=True)

# 色の定義
BG=(0,0,0,0); RC=(169,169,169,255); RK=(105,105,105,255)

# 投石用の小さな石のピクセルデータ
projectile_data = [
    [BG, BG, RC, RC, BG, BG],
    [BG, RC, RK, RC, RC, BG],
    [RC, RC, RC, RK, RC, RC],
    [RC, RC, RK, RC, RC, BG],
    [BG, RC, RC, RC, BG, BG],
    [BG, BG, RC, BG, BG, BG],
]

def create_image_from_data(data, filename):
    # 元のピクセルデータのサイズで作成
    height = len(data)
    width = len(data[0])
    img = Image.new('RGBA', (width, height))
    for y in range(height):
        for x in range(width):
            img.putpixel((x, y), data[y][x])
    
    filepath = os.path.join(assets_path, filename)
    img.save(filepath)
    print(f"'{filepath}' を生成しました。")

create_image_from_data(projectile_data, "rock_projectile.png")
print("画像の生成が完了しました。")