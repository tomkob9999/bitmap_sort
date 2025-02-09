import math
import time
import pandas as pd
import random

"""
TwoLayerBitmap Class
----------------------
This class implements a multi-layered bitmap data structure designed to efficiently handle sorting, duplicates, non-integer values, and negative values. 

Key Features:
- Supports insertion, deletion, and retrieval of sorted values.
- Handles non-integer values using precision scaling.
- Manages negative values by offsetting them to a positive range.
- Dynamically adjusts the size of the bitmap layers to fit power-of-2 constraints.

Parameters:
- size (int): The initial size of the bitmap.
- precision (int): The number of decimal places for scaling non-integer values.
- all_integer (bool): If True, skips scaling and offset adjustments for optimization.
- input_list (list, optional): A list of initial values to insert.

Main Methods:
- insert(value): Inserts a value into the bitmap.
- delete(value): Removes a value from the bitmap.
- contains(value): Checks if a value is in the bitmap.
- traverse_sorted(): Returns the sorted list of values, handling scaling and offset reversal when needed.

Extensions Implemented:
1. Multi-layered bitmap structure for efficient storage and traversal.
2. Precision scaling for non-integer values (optional via all_integer flag).
3. Offset-based handling for negative values (optional via all_integer flag).
4. Automatic size adjustment to ensure efficient bitmap allocation.
5. Duplicate handling using a count-based system.
"""
class TwoLayeredBitmap:
    def __init__(self, size, precision=0, all_integer=True, input_list=None):
        self.all_integer = all_integer  # Optimization flag
        self.precision = 10 ** precision if not all_integer else 1
        self.offset = 0  # Offset for handling negative numbers

        # Determine minimum value for offset and adjust input list if necessary
        if input_list and not all_integer:
            min_value = min(input_list)
            self.offset = -math.floor(min_value * self.precision) if min_value < 0 else 0
            input_list = [math.floor(x * self.precision) + self.offset for x in input_list]

        # Adjust size to the nearest power of 2 to handle offset and precision
        self.size = 1 << (math.ceil(math.log2(size * 2)))  # Ensure space for negative values and scaling
        self.layer_size = int(math.sqrt(self.size))
        self.duplicates = {}  # Track counts of duplicates only when needed

        print(f"Bitmap size of base layer: {self.layer_size}")

        # Initialize bitmaps using dictionaries to dynamically create them only when needed
        self.base_layer = [0] * self.layer_size  # Base layer (1D bitmap)
        self.second_layer = {}  # Sparse second layer

        # Insert initial input list if provided
        if input_list:
            for num in input_list:
                self.insert(num)

    def _adjust_value(self, value):
        if self.all_integer:
            return value  # No scaling or offset needed
        return math.floor(value * self.precision) + self.offset

    def _revert_value(self, value):
        if self.all_integer:
            return value  # No scaling or offset reversal needed
        return (value - self.offset) / self.precision

    def insert(self, value):
        num = self._adjust_value(value)
        if 0 <= num < self.size:
            if self.contains(value):
                # Increment duplicate count only if it already exists
                if num in self.duplicates:
                    self.duplicates[num] += 1
                else:
                    self.duplicates[num] = 2  # Start counting from 2 since it’s a duplicate now
                return  # No need to update bitmaps for duplicates

            base_index = num // self.layer_size
            bit_position = num % self.layer_size

            # Set the bit in the base layer
            self.base_layer[base_index] |= (1 << bit_position)

            # Dynamically create and set the bit in the second layer if needed
            if base_index not in self.second_layer:
                self.second_layer[base_index] = 0
            self.second_layer[base_index] |= (1 << bit_position)

    def delete(self, value):
        num = self._adjust_value(value)
        if num in self.duplicates:
            # Decrement the duplicate count
            self.duplicates[num] -= 1
            if self.duplicates[num] == 0:
                del self.duplicates[num]  # Remove the entry if count reaches 0
                self._clear_bit(num)  # Clear the bit from the bitmap
        elif self.contains(value):
            self._clear_bit(num)  # Clear the bit if no duplicates are left

    def _clear_bit(self, num):
        base_index = num // self.layer_size
        bit_position = num % self.layer_size

        # Unset the bit in the second layer
        if base_index in self.second_layer:
            self.second_layer[base_index] &= ~(1 << bit_position)
            if self.second_layer[base_index] == 0:
                del self.second_layer[base_index]  # Clean up if no bits are set
                self.base_layer[base_index] &= ~(1 << bit_position)  # Unset the bit in the base layer

    def contains(self, value):
        num = self._adjust_value(value)
        if 0 <= num < self.size:
            base_index = num // self.layer_size
            bit_position = num % self.layer_size

            # Check the base layer first
            if (self.base_layer[base_index] & (1 << bit_position)) == 0:
                return False

            # Then check the second layer
            return (self.second_layer[base_index] & (1 << bit_position)) != 0
        return False

    def find_next_inbm(self, bitmap, bit_position):
        """Find the next set bit in a given bitmap starting from bit_position."""
        remaining_bits = bitmap >> bit_position
        if remaining_bits != 0:
            return bit_position + (remaining_bits & -remaining_bits).bit_length() - 1
        return None

    def find_previous_inbm(self, bitmap, bit_position):
        """Find the previous set bit in a given bitmap starting from bit_position."""
        if bit_position == 0:
            return None
        mask = (1 << bit_position) - 1  # Mask to restrict search to lower bits
        remaining_bits = bitmap & mask
        if remaining_bits != 0:
            return remaining_bits.bit_length() - 1  # Return the position of the most significant bit
        return None

    def find_next(self, value):
        num = self._adjust_value(value)
        if num + 1 >= self.size:
            return None

        base_index = (num + 1) // self.layer_size
        bit_position = (num + 1) % self.layer_size

        # Search within the current second-layer bitmap using bitwise operations
        if base_index in self.second_layer:
            next_bit_position = self.find_next_inbm(self.second_layer[base_index], bit_position)
            if next_bit_position is not None:
                return self._revert_value(base_index * self.layer_size + next_bit_position)

        # Find the next base-layer bit using bitwise operations
        next_base_index = self.find_next_inbm(self.base_layer[base_index], 0)
        if next_base_index is not None:
            return self._revert_value(next_base_index * self.layer_size)

        return None  # No next element found

    def traverse_sorted_reverse(self):
        sorted_elements = []

        # Traverse base layer in reverse
        for base_index in reversed(range(self.layer_size)):
            if self.base_layer[base_index] != 0:  # If any bit is set
                # Traverse corresponding second layer in reverse
                bitmap = self.second_layer.get(base_index, 0)
                bit_position = self.layer_size - 1

                # Find all set bits in reverse order
                while True:
                    prev_bit_position = self.find_previous_inbm(bitmap, bit_position)
                    if prev_bit_position is None:
                        break
                    element = base_index * self.layer_size + prev_bit_position
                    count = self.duplicates.get(element, 1)  # Default to 1 if no duplicates
                    original_value = self._revert_value(element)
                    sorted_elements.extend([original_value] * count)  # Add duplicates
                    bit_position = prev_bit_position - 1  # Move to the previous bit

        return sorted_elements

    def traverse_sorted(self):
        sorted_elements = []

        # Traverse base layer
        for base_index in range(self.layer_size):
            if self.base_layer[base_index] != 0:  # If any bit is set
                # Traverse corresponding second layer
                bitmap = self.second_layer.get(base_index, 0)
                bit_position = 0

                # Find all set bits in the second layer
                while True:
                    next_bit_position = self.find_next_inbm(bitmap, bit_position)
                    if next_bit_position is None:
                        break
                    element = base_index * self.layer_size + next_bit_position
                    count = self.duplicates.get(element, 1)  # Default to 1 if no duplicates
                    original_value = self._revert_value(element)
                    sorted_elements.extend([original_value] * count)  # Add duplicates
                    bit_position = next_bit_position + 1  # Move to the next bit

        return sorted_elements

# Example usage and testing
def run_test(size, element_step):
    test_bitmap = MultiLayerBitmap(size)  # Initialize the bitmap

    # Insert test
    start_time = time.time()
    for i in range(0, size, element_step):  # Insert sparse values
        test_bitmap.insert(i)
    insertion_time = time.time() - start_time

    # Contains test (middle element)
    contains_value = (size // 2) - ((size // 2) % element_step)  # Closest inserted value to the middle
    start_time = time.time()
    contains_result = test_bitmap.contains(contains_value)
    contains_time = time.time() - start_time

    # Find next test
    start_time = time.time()
    next_result = test_bitmap.find_next(contains_value)
    next_time = time.time() - start_time

    # Find previous test
    start_time = time.time()
    previous_result = test_bitmap.find_previous_inbm(test_bitmap.base_layer[0], 0)  # Simulate previous bit
    previous_time = time.time() - start_time

    # Traverse sorted test
    start_time = time.time()
    sorted_traversal = test_bitmap.traverse_sorted()
    traversal_time = time.time() - start_time

    # Random duplicates test
    range_size = 256  # Define a range with a perfect square root for correct layer sizing
    input_size = range_size // 2  # Generate inputs half of the range to encourage duplicates
    random_input = [random.randint(0, range_size - 1) for _ in range(input_size)]
    
    bitmap_with_random_duplicates = MultiLayerBitmap(range_size)
    for num in random_input:
        bitmap_with_random_duplicates.insert(num)
    random_duplicates_output = bitmap_with_random_duplicates.traverse_sorted()
    print("Random Duplicates Test Output:", random_duplicates_output)
    print("duplicates", bitmap_with_random_duplicates.duplicates)


    # Return the results for this test
    return {
        "Test Data Size": len(sorted_traversal),
        "Insertion Time (s)": insertion_time,
        "Contains Time (s)": contains_time,
        "Next Time (s)": next_time,
        "Previous Time (s)": previous_time,
        "Traversal Time (s)": traversal_time
    }

if __name__ == "__main__":
    # Test configurations
    sizes = [100, 10000, 1_000_000]  # Corrected sizes to satisfy multi-layer design requirements
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
