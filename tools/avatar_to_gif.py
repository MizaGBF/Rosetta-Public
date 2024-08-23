from PIL import Image
import math
import subprocess
import traceback

HALF_MAX_FRAMES = 30
PAUSE_FRAMES = 20
ICON_RATION = 5
CIRCLE_PLACEMENTS = 16
ANIMATION_STEP_RATIO = 2.5 # must be at least 2
PLACEMENT_DEGREE = 360 / CIRCLE_PLACEMENTS

def ask_path(question : str) -> str:
    s = ""
    while s == "":
        s = input(question).strip()
    return s

def paste(base : Image, icon: Image, position : tuple) -> Image:
    layer = Image.new('RGB', base.size, "black")
    layer_a = Image.new("L", base.size, "black")
    layer.putalpha(layer_a)
    layer_a.close()
    layer.paste(icon, position, icon)
    tmp = Image.alpha_composite(base, layer)
    base.close()
    base = tmp
    layer.close()
    return base

def run():
    frames = []
    try:
        with Image.open(ask_path("Input path of base image to animate:")) as base:
            with Image.open(ask_path("Input path of icon animation:")) as icon:
                print("Base size is:", base.size)
                if base.size[0] != base.size[1]:
                    raise Exception("Image isn't square")
                half_size = (base.size[0] / 2, base.size[1] / 2)
                icon_size = int(base.size[0] / ICON_RATION)
                half_icon_size = icon_size / 2
                print("Icon size sets to:", icon_size)
                with icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS) as resized:
                    step = icon_size * ANIMATION_STEP_RATIO / HALF_MAX_FRAMES
                    offset = icon_size * 2
                    for j in range(2):
                        for f in range(HALF_MAX_FRAMES):
                            frames.append(base.copy())
                            for i in range(CIRCLE_PLACEMENTS):
                                x = - half_icon_size + half_size[0] + (half_size[0] + offset) * math.cos(math.radians(i * PLACEMENT_DEGREE))
                                y = - half_icon_size + half_size[1] + (half_size[1] + offset) * math.sin(math.radians(i * PLACEMENT_DEGREE))
                                frames[-1] = paste(frames[-1], resized, (int(x), int(y)))
                            if j == 0: offset -= step
                            else: offset +=step
                        if j == 0:
                            angle_step = PLACEMENT_DEGREE * 2 / PAUSE_FRAMES
                            for k in range(PAUSE_FRAMES):
                                frames.append(base.copy())
                                for i in range(CIRCLE_PLACEMENTS):
                                    x = - half_icon_size + half_size[0] + (half_size[0] + offset) * math.cos(math.radians(i * PLACEMENT_DEGREE + angle_step * (k+1)))
                                    y = - half_icon_size + half_size[1] + (half_size[1] + offset) * math.sin(math.radians(i * PLACEMENT_DEGREE + angle_step * (k+1)))
                                    frames[-1] = paste(frames[-1], resized, (int(x), int(y)))
                frames[0].save('output.gif', save_all=True, append_images=frames[1:], optimize=True, duration=30, loop=0)
                print("output.gif created")
                for f in frames:
                    try: f.close()
                    except: pass
        try:
            subprocess.run(['gifsicle', '-i', 'output.gif', '-O3', '--colors', '256', '-o', 'output-optimized.gif'])
            print("output-optimized.gif should be created")
        except:
            print("gifsicle.exe must be in this folder to optimize the gif")
        
    except Exception as e:
        print("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        for f in frames:
            try: f.close()
            except: pass

if __name__ == "__main__":
    run()