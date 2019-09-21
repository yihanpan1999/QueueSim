#!/bin/bash

python Simulation.py --dataroot 'random' --policy 1 --ri 60
python Simulation.py --dataroot 'random' --policy 4 --ri 60
python Simulation.py --dataroot 'random' --policy 1 --ri 120
python Simulation.py --dataroot 'random' --policy 4 --ri 120
python Simulation.py --dataroot 'first_half' --policy 1 --ri 60
python Simulation.py --dataroot 'first_half' --policy 4 --ri 60
python Simulation.py --dataroot 'first_half' --policy 1 --ri 120
python Simulation.py --dataroot 'first_half' --policy 4 --ri 120

