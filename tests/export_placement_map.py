"""Export this workspace's Warehouse navigation map as Unity's placement constraint.

No geometry is inferred or changed. The saved ROS map remains authoritative for
Nav2; this mask keeps random tasks out of cells that it considers occupied.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from PIL import Image


def export(map_dir, output):
    yaml = map_dir / 'map.yaml'
    image = map_dir / 'short_map.png'
    expected = ('image: short_map.png', 'resolution: 0.1', 'origin: [-40,-40,0]',
                'occupied_thresh: 0.5', 'free_thresh: 0.5', 'negate: 0')
    if yaml.read_text().splitlines() != list(expected):
        raise ValueError('Unsupported map configuration; update exporter explicitly')
    im = Image.open(image).convert('RGB')
    width, height = im.size
    data = bytearray((width*height+7)//8)
    for y in range(height):
        for x in range(width):
            # nav2 map_server trinary mode, negate=false, free threshold=0.5.
            if sum(im.getpixel((x, height-1-y))) / 3 > 127.5:
                index = y*width+x
                data[index//8] |= 1 << (index % 8)
    record = dict(width=width, height=height, resolution=0.1, originX=-40, originY=-40,
                  freeCells=base64.b64encode(data).decode(),
                  source='social_sim_ros/social_sim_ros/maps/warehouse',
                  sourceCommit='2ac78a303d323fbce0caad83555dbe940cc40435',
                  yamlSha256=hashlib.sha256(yaml.read_bytes()).hexdigest(),
                  imageSha256=hashlib.sha256(image.read_bytes()).hexdigest())
    output.write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('map_dir', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export(args.map_dir, args.output)
