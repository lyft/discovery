import sys
import os

discovery_parent_dir = '/'.join(os.getcwd().split('/')[:-2])
sys.path.append(discovery_parent_dir)

