import os
import xml.etree.ElementTree as ET

CLASSES = {"pothole": 0}

def convert_bbox(img_w, img_h, xmin, ymin, xmax, ymax):
    x_center = ((xmin + xmax) / 2) / img_w
    y_center = ((ymin + ymax) / 2) / img_h
    width = (xmax - xmin) / img_w
    height = (ymax - ymin) / img_h
    return x_center, y_center, width, height

def convert_all_xmls():
    xml_dir = "xmls"
    label_dir = "labels/train"

    os.makedirs(label_dir, exist_ok=True)

    for file in os.listdir(xml_dir):
        if not file.endswith(".xml"):
            continue

        xml_path = os.path.join(xml_dir, file)
        tree = ET.parse(xml_path)
        root = tree.getroot()

        size = root.find("size")
        if size is None:
            continue

        img_w = int(size.find("width").text)
        img_h = int(size.find("height").text)

        txt_name = file.replace(".xml", ".txt")
        txt_path = os.path.join(label_dir, txt_name)

        with open(txt_path, "w") as f:
            for obj in root.findall("object"):
                name = obj.find("name").text
                if name not in CLASSES:
                    continue

                bbox = obj.find("bndbox")
                xmin = float(bbox.find("xmin").text)
                ymin = float(bbox.find("ymin").text)
                xmax = float(bbox.find("xmax").text)
                ymax = float(bbox.find("ymax").text)

                x, y, w, h = convert_bbox(img_w, img_h, xmin, ymin, xmax, ymax)
                f.write(f"{CLASSES[name]} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")

    print("✅ All XML files converted to YOLO format")

if __name__ == "__main__":
    convert_all_xmls()
