for i in {1..1}; do
    echo python Simulation.py --dataroot "random" --policy 1 --ri 60
    python Simulation.py --dataroot "random" --policy 1 --ri 60
    echo python Simulation.py --dataroot "first_half" --policy 1 --ri 60
    python Simulation.py --dataroot "first_half" --policy 1 --ri 60
    echo python Simulation.py --dataroot "first_slots" --policy 1 --ri 60
    python Simulation.py --dataroot "first_slots" --policy 1 --ri 60
    echo python Simulation.py --dataroot "adaptive" --policy 1 --ri 60
    python Simulation.py --dataroot "adaptive" --policy 1 --ri 60
done 