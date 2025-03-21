#!/usr/bin/env python3
import socket
import time
import sys

def check_connectivity(host, port, timeout=5):
    """Check if a host:port is reachable"""
    print(f"Checking connectivity to {host}:{port}...")
    start_time = time.time()
    
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set a timeout
        s.settimeout(timeout)
        # Try to connect
        result = s.connect_ex((host, port))
        s.close()
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result == 0:
            print(f"✅ Connection to {host}:{port} SUCCESS in {duration:.2f}s")
            return True
        else:
            print(f"❌ Connection to {host}:{port} FAILED with error code {result} in {duration:.2f}s")
            return False
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Error checking connectivity to {host}:{port}: {str(e)} in {duration:.2f}s")
        return False

def run_dns_lookup(hostname):
    """Perform a DNS lookup for a hostname"""
    print(f"Performing DNS lookup for {hostname}...")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ DNS lookup successful: {hostname} resolves to {ip}")
        return ip
    except socket.gaierror as e:
        print(f"❌ DNS lookup failed for {hostname}: {str(e)}")
        return None

if __name__ == "__main__":
    print("\n--- Network Connectivity Diagnostics ---\n")
    
    # Check DNS for EventHub emulator
    eventhubs_ip = run_dns_lookup("eventhubs-emulator")
    
    # Check critical services
    services = [
        ("eventhubs-emulator", 5672),  # AMQP
        ("eventhubs-emulator", 9092),  # Kafka
        ("eventhubs-emulator", 5300),  # REST API
        ("redis", 6379),               # Redis
        ("postgres", 5432)             # PostgreSQL
    ]
    
    print("\n--- Connection Tests ---\n")
    results = {}
    
    for host, port in services:
        results[(host, port)] = check_connectivity(host, port)
    
    print("\n--- Summary ---\n")
    all_success = True
    
    for (host, port), success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{host}:{port} - {status}")
        if not success:
            all_success = False
    
    print("\nDiagnostic completed.")
    sys.exit(0 if all_success else 1) 