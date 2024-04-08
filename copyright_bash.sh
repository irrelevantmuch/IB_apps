#!/bin/bash

# Define the path to search in, "." means the current directory
SEARCH_PATH="."

# Find all .py files in the specified path and its subdirectories
find "$SEARCH_PATH" -type f -name '*.py' | while read i; do
  # Check if the file does not contain the word "Copyright"
  if ! grep -q "Copyright" "$i"; then
    # If not, prepend the copyright header to the file
    cat junkFolder/copyright_header.txt "$i" > "$i".new && mv "$i".new "$i"
  fi
done