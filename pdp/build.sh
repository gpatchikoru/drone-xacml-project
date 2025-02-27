#!/bin/bash

# Set paths
BALANA_HOME="$(pwd)"
BALANA_LIBS="$BALANA_HOME/lib"

# Create lib directory if it doesn't exist
mkdir -p lib

# Find all jar files in the balana distribution
CLASSPATH=""
for jar in $(find . -name "*.jar"); do
  if [ -z "$CLASSPATH" ]; then
    CLASSPATH="$jar"
  else
    CLASSPATH="$CLASSPATH:$jar"
  fi
  
  # Copy to lib directory for easier management
  cp "$jar" lib/
done

# Compile the server
javac -cp "$CLASSPATH" src/SimplePDPServer.java

# Create policies directory if it doesn't exist
mkdir -p policies

echo "Compilation complete. To run the server, use:"
echo "./run.sh"