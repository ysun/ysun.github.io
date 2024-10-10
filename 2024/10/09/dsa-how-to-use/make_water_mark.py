#!/bin/python3
from PIL import Image, ImageDraw, ImageFont
 
def add_watermark(image_path, watermark_text, output_path):
    # 打开图片
    image = Image.open(image_path)
    # 创建一个可以在上面绘图的空白图层
    draw = ImageDraw.Draw(image)
    # 设置水印文字的字体和大小
    font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoKufiArabic-Regular.ttf", 30)
    # 设置水印文字的颜色
    fill_color = (255, 0, 0, 128)  # RGBA格式，最后一位是透明度
    # 计算水印文字的位置
    width, height = image.size
    watermark_width, watermark_height = draw.textsize(watermark_text, font)
    x = width - watermark_width
    y = height - watermark_height
    # 在图片上绘制水印文字
    draw.text((x, y), watermark_text, font=font, fill=fill_color)
    # 保存新的图片
    image.save(output_path)
    # 关闭图片
    image.close()
 
# 使用示例
image_path = 'dsa-usage2.png'
watermark_text = '一颗烂樱桃'
output_path = 'dsa-usage-watermark.jpg'
 
add_watermark(image_path, watermark_text, output_path)
