#!/bin/bash

# Set paths
BALANA_HOME="$(pwd)"
BALANA_LIBS="$BALANA_HOME/lib"

# Build classpath with all jar files
CLASSPATH=".:$BALANA_HOME/src"
for jar in "$BALANA_LIBS"/*.jar; do
  CLASSPATH="$CLASSPATH:$jar"
done

# Set policy location for FileBasedPolicyFinderModule
export BALANA_CONFIG_DIR="$BALANA_HOME/policies"

# Run the server
java -cp "$CLASSPATH" SimplePDPServer