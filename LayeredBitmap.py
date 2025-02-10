# | Word | Layers | Bits            | Bytes           | Bits (Formatted) | Bytes (Formatted) |
# |------|--------|-----------------|-----------------|------------------|-------------------|
# | 32   | 5      | 33,554,432      | 4,194,304       | 33.6Mb           | 4.2MB             |
# | 32   | 6      | 1,073,741,824   | 134,217,728     | 1.1Gb            | 134.2MB           |
# | 64   | 5      | 1,073,741,824   | 134,217,728     | 1.1Gb            | 134.2MB           |
# | 32   | 7      | 34,359,738,368  | 4,294,967,296   | 34.4Gb           | 4.3GB             |
# | 64   | 6      | 68,719,476,736  | 8,589,934,592   | 68.7Gb           | 8.6GB             |
# | 32   | 8      | 1,099,511,627,776 | 137,438,953,472 | 1.1Tb            | 137.4GB           |
# | 64   | 7      | 4,398,046,511,104 | 549,755,813,888 | 4.4Tb            | 549.8GB           |
# | 64   | 8      | 281,474,976,710,656 | 35,184,372,088,832 | 281.5Tb     | 35.2TB            |

class BitmapCore:
    """
    Represents a core bitmap with a given size and layers, capable of managing
    individual bits and hierarchical child relationships.
    """
    def __init__(self, size, num_layers, bitmap=None):
        if size <= 0:
            raise ValueError("Size must be a positive integer.")
        self.size = size
        # Initialize the bitmap with the given parameter or default to 0
        if bitmap is not None:
            if not isinstance(bitmap, int) or bitmap < 0:
                raise ValueError("Bitmap must be a non-negative integer.")
            if bitmap >= (1 << size):
                raise ValueError("Bitmap exceeds the size limit.")
            self.bitmap = bitmap
        else:
            self.bitmap = 0
        # Initialize an array of children with the same length as the binary object
        self.children = [None] * size
        self.parent = None
        self.parent_index = 0
        self.lower_bound = 0
        self.layer = 0
        # if not num_layers:
        self.num_layers = num_layers

    def set_bit(self, index, value):
        """Set a specific bit in the bitmap to 0 or 1."""
        if index < 0 or index >= self.size:
            raise IndexError("Bit index out of range.")
        if value not in (0, 1):
            raise ValueError("Bit value must be 0 or 1.")
        if value == 1:
            self.bitmap |= (1 << index)  # Set the bit to 1
        else:
            self.bitmap &= ~(1 << index)  # Set the bit to 0

    def get_bit(self, index):
        """Get the value of a specific bit in the bitmap."""
        if index < 0 or index >= self.size:
            raise IndexError("Bit index out of range.")
        return (self.bitmap >> index) & 1

    def assign_child(self, index, child):
        """Assign a child BitmapCore object at the specified index."""
        if index < 0 or index >= self.size:
            raise IndexError("Child index out of range.")
        if not isinstance(child, BitmapCore):
            raise TypeError("Child must be an instance of BitmapCore.")
        self.children[index] = child
        child.parent = self
        child.parent_index = index
        child.layer = self.layer + 1
        child.lower_bound = self.lower_bound + (index)*self.size**(self.num_layers-self.layer-1)
        child.num_layers = self.num_layers

    def get_child(self, index):
        """Retrieve the child object at the specified index."""
        if index < 0 or index >= self.size:
            raise IndexError("Child index out of range.")
        return self.children[index]

    def drop_child(self, index):
        """Delete the child object at the specified index and assign None."""
        if index < 0 or index >= self.size:
            raise IndexError("Child index out of range.")
        self.children[index] = None

    def _find_next_bm(b, pos):
        # Step 1: Offset input by -1 for 0-based indexing
        pos -= 1
        
        # Step 2: Mask out bits up to and including `pos`
        masked_b = b & ~((1 << (pos + 1)) - 1)
        
        # Step 3: If no bits are set after `pos`, return -1
        if masked_b == 0:
            return -1
            # return 0
        
        # Step 4: Find the least significant set bit (LSB)
        lsb = masked_b & -masked_b
        
        # Step 5: Convert the LSB to the correct bit position (1-based indexing)
        return lsb.bit_length()
    
    def _find_previous_bm(b, pos):
        # Step 1: Mask out bits strictly above `pos`
        x1 = b & ((1 << pos) - 1)
        
        # Step 2: If no bits are set, return -1
        if x1 == 0:
            # return 0
            return -1
        
        # Step 3: Isolate the most significant set bit using bitwise operations
        # return x1.bit_length() - 1
        return x1.bit_length()

    
    def find_next(self, pos):
        return BitmapCore._find_next_bm(self.bitmap, pos)
        
    def find_previous(self, pos):
        return BitmapCore._find_previous_bm(self.bitmap, pos)
        
    def __repr__(self):
        """Return a string representation of the BitmapCore object."""
        binary_str = bin(self.bitmap)[2:].zfill(self.size)
        return f"BitmapCore(size={self.size}, bitmap={binary_str}, children_count={sum(1 for child in self.children if child is not None)}), layer={self.layer}, lower_bound={self.lower_bound}, parent_index={self.parent_index}"



class LayeredBitmap:
    """
    Hierarchical bitmap to store integers to bitmaps.  Initial only the base bitmap exists which less than the CPU word size (32 or 64).  
    It generates upper layers only if the value exists.  All the values are represented, in the leaf bitmaps.  Bits in lower layers indicates the existence of any values above.
    """
    
    def __init__(self, num_layers=6, bitmap_size=64):
        if num_layers < 5 and num_layers > 8:
            raise ValueError("Number of layers must be between 5 and 8. Upper range is calculated by bitmap_size^num_layers. Defaults are num_layers=6 and bitmap_size=64 (0 - 68,719,476,736)")
        if bitmap_size not in [32, 64]:
            raise ValueError("Bitmap size must be 32 or 64. Upper range is calculated by bitmap_size^num_layers. Defaults are num_layers=6 and bitmap_size=64 (0 - 68,719,476,736)")
        
        self.num_layers = num_layers
        self.base_bitmap = BitmapCore(size=bitmap_size, num_layers=num_layers, bitmap=0b0)
        self.bitmap_size = bitmap_size

    def set(self, pos):
        # print("SET self.num_layers", self.num_layers)
        """Set the bit corresponding to the given position across the layers."""
        if pos < 0 or pos >= self.base_bitmap.size**self.num_layers:
            raise ValueError("Position out of range.")

        # print("pos", pos)
        chopper = self.base_bitmap.size**(self.num_layers-1)
        relative_pos = pos // chopper

        self.base_bitmap.set_bit(relative_pos, 1)

        
        if not self.base_bitmap.children[relative_pos]:
            self.base_bitmap.assign_child(relative_pos, BitmapCore(size=self.bitmap_size, num_layers=self.num_layers, bitmap=0b0))

        target_bitmap = self.base_bitmap.children[relative_pos]
        
        offset_sofar = relative_pos*chopper
        
        for layer_index in range(1, self.num_layers, 1):
            chopper = self.base_bitmap.size**(self.num_layers-layer_index-1)
            pospos = pos - offset_sofar
            relative_pos = pospos // chopper
            target_bitmap.set_bit(relative_pos, 1)
            if layer_index < self.num_layers-1:
                if not target_bitmap.children[relative_pos]:
                    target_bitmap.assign_child(relative_pos, BitmapCore(size=self.bitmap_size, num_layers=self.num_layers, bitmap=0b0))
                target_bitmap = target_bitmap.children[relative_pos]
                offset_sofar = offset_sofar+relative_pos*chopper


    def get(self, pos):
        if pos < 0 or pos >= self.base_bitmap.size**self.num_layers:
            raise ValueError("Position out of range.")

        chopper = self.base_bitmap.size**(self.num_layers-1)
        relative_pos = pos // chopper
        
        if not self.base_bitmap.children[relative_pos]:
            raise ValueError("The whole bitmap is empty.")

        target_bitmap = self.base_bitmap.children[relative_pos]
        
        offset_sofar = relative_pos*chopper
        
        for layer_index in range(1, self.num_layers, 1):
            chopper = self.base_bitmap.size**(self.num_layers-layer_index-1)
            pospos = pos - offset_sofar
            relative_pos = pospos // chopper
            if layer_index < self.num_layers-1:
                if not target_bitmap.children[relative_pos]:
                    return 0b0
                target_bitmap = target_bitmap.children[relative_pos]
                    
                offset_sofar = offset_sofar+relative_pos*chopper
            else:
                return target_bitmap.get_bit(relative_pos)

    def go_current(self, pos):
        if pos < 0 or pos >= self.base_bitmap.size**self.num_layers:
            raise ValueError("Position out of range.")

        chopper = self.base_bitmap.size**(self.num_layers-1)
        relative_pos = pos // chopper
        
        if not self.base_bitmap.children[relative_pos]:
            return self.base_bitmap, relative_pos

        target_bitmap = self.base_bitmap.children[relative_pos]
        
        offset_sofar = relative_pos*chopper
        prev_pos = relative_pos
        # Generate layer-wise dependencies
        for layer_index in range(1, self.num_layers, 1):
            prev_pos = relative_pos
            chopper = self.base_bitmap.size**(self.num_layers-layer_index-1)
            pospos = pos - offset_sofar
            relative_pos = pospos // chopper
            if layer_index < self.num_layers-1:
                if not target_bitmap.children[relative_pos]:
                    return target_bitmap, relative_pos
                target_bitmap = target_bitmap.children[relative_pos]
                    
                offset_sofar = offset_sofar+relative_pos*chopper
            else:
                return target_bitmap, relative_pos
    
    def find_next(self, pos):

        target, curpos = self.go_current(pos)
        if not target:
            return 0
        parent = target
        parent_index = curpos
        # while True:
        for i in range(10):
            if i > 0:
                parent = parent.parent
            no_parent = False
            ret = False
            if not parent:
                return -1
            ret = parent.find_next(parent_index+1)
            if ret > -1:
                previous_ret = ret
                child = parent
                for j in range(10):
                    prev_child = child
                    child = child.children[ret-1]
                    if not child:
                        return prev_child.lower_bound + ret - 1
                    ret = child.find_next(0)
                return -100000
            parent_index = parent.parent_index
        return -100000


    def find_previous(self, pos):

        target, curpos = self.go_current(pos)
        if not target:
            return 0
        parent = target
        parent_index = curpos
        # while True:
        for i in range(10):
            if i > 0:
                parent = parent.parent
            no_parent = False
            ret = False
            if not parent:
                return -1
            ret = parent.find_previous(parent_index)
            if ret > -1:
                previous_ret = ret
                child = parent
                for j in range(10):
                    prev_child = child
                    child = child.children[ret-1]
                    if not child:
                        return prev_child.lower_bound + ret - 1
                    ret = child.find_previous(self.bitmap_size)
                return -100000
            parent_index = parent.parent_index
        return -100000

    def traverse_forward(self, pos=0):
        ret = pos
        num_loops = self.bitmap_size**(self.num_layers)
        output = []
        for i in range(num_loops):
            ret = self.find_next(ret)
            if ret == -1:
                return output
            output.append(ret)

    def traverse_backward(self, pos=0):
        num_loops = self.bitmap_size**(self.num_layers)
        ret = pos if pos else num_loops-1
        output = []
        for i in range(num_loops):
            ret = self.find_previous(ret)
            if ret == -1:
                return output
            output.append(ret)
    
    def insert(self, vals):
        for v in vals:
            self.set(v)





import time
import pandas as pd

# Example usage and testing
def run_test(size, element_step):
    test_bitmap = LayeredBitmap()

    # Insert test
    start_time = time.time()
    vals = [i for i in range(0, size, element_step)]
    test_bitmap.insert(vals)
    insertion_time = time.time() - start_time

    # Contains test (middle element)
    contains_value = (size // 2) - ((size // 2) % element_step)  # Closest inserted value to the middle
    start_time = time.time()
    contains_result = test_bitmap.get(contains_value)
    contains_time = time.time() - start_time

    # Set test (middle element)
    start_time = time.time()
    contains_result = test_bitmap.set(contains_value)
    set_time = time.time() - start_time
    
    # Find next test
    start_time = time.time()
    next_result = test_bitmap.find_next(contains_value)
    next_time = time.time() - start_time

    # Find previous test
    start_time = time.time()
    next_result = test_bitmap.find_previous(contains_value)
    previous_time = time.time() - start_time

    # Traverse sorted test
    start_time = time.time()
    sorted_traversal = test_bitmap.traverse_forward()
    traversal_time = time.time() - start_time


    # Return the results for this test
    return {
        "Test Data Size": int(len(vals)),
        "Insertion Time (s)": set_time,
        "Contains Time": contains_time,
        "Bulk Insert Time (sorting)": insertion_time,
        "Next Time (s)": next_time,
        "Previous Time (s)": previous_time,
        "Traversal Time": traversal_time
    }


# Test configurations
sizes = [100, 10000, 1_000_000]  # Corrected sizes to satisfy multi-layer design requirements
# sizes = [100, 10000, 100000]  # Corrected sizes to satisfy multi-layer design requirements
element_step = 10  # Sparse test with step size

# Run and collect results
results = [run_test(size, element_step) for size in sizes]

# Create DataFrame and reorganize metrics as rows and sizes as columns
df = pd.DataFrame(results).T
df.columns = [f"Size {sizes[i]}" for i in range(len(results))]

# Calculate change rates manually
if len(df.columns) > 1:
    change_rate_1_2 = ((df.iloc[:, 1] - df.iloc[:, 0]) / df.iloc[:, 0]).replace([float('inf'), -float('inf')], 0).fillna(0)
    df["Change Rate 1-2"] = change_rate_1_2.values

if len(df.columns) > 2:
    change_rate_2_3 = ((df.iloc[:, 2] - df.iloc[:, 1]) / df.iloc[:, 1]).replace([float('inf'), -float('inf')], 0).fillna(0)
    df["Change Rate 2-3"] = change_rate_2_3.values

print(df)