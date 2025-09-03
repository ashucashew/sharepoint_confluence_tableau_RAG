#!/usr/bin/env python3
"""
Test script to demonstrate incremental sync functionality
"""

import asyncio
import json
from datetime import datetime, timedelta
from data_connectors import DataSyncManager
from loguru import logger

async def test_incremental_sync():
    """Test the incremental sync functionality"""
    
    print("🧪 Testing Incremental Sync Functionality")
    print("=" * 50)
    
    # Initialize sync manager
    sync_manager = DataSyncManager()
    await sync_manager.initialize()
    
    print("\n1️⃣ First sync (should be full sync)")
    print("-" * 30)
    
    # First sync - should be full sync
    result = await sync_manager.sync_all_sources()
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        sync_data = result.get('result', {})
        print(f"Overall Strategy: {sync_data.get('overall_sync_strategy')}")
        print(f"Documents Processed: {sync_data.get('documents_processed')}")
        print(f"Documents Added: {sync_data.get('documents_added')}")
        print(f"Documents Updated: {sync_data.get('documents_updated')}")
        
        # Show source results
        for source_result in sync_data.get('source_results', []):
            print(f"  {source_result['source']}: {source_result['strategy']} - {source_result['added']} added, {source_result['updated']} updated")
    
    print("\n2️⃣ Second sync (should be incremental)")
    print("-" * 30)
    
    # Second sync - should be incremental
    result2 = await sync_manager.sync_all_sources()
    print(f"Status: {result2.get('status')}")
    if result2.get('status') == 'success':
        sync_data = result2.get('result', {})
        print(f"Overall Strategy: {sync_data.get('overall_sync_strategy')}")
        print(f"Documents Processed: {sync_data.get('documents_processed')}")
        print(f"Documents Added: {sync_data.get('documents_added')}")
        print(f"Documents Updated: {sync_data.get('documents_updated')}")
        
        # Show source results
        for source_result in sync_data.get('source_results', []):
            print(f"  {source_result['source']}: {source_result['strategy']} - {source_result['added']} added, {source_result['updated']} updated")
    
    print("\n3️⃣ Force full sync")
    print("-" * 30)
    
    # Force full sync
    result3 = await sync_manager.force_full_sync()
    print(f"Status: {result3.get('status')}")
    if result3.get('status') == 'success':
        sync_data = result3.get('result', {})
        print(f"Overall Strategy: {sync_data.get('overall_sync_strategy')}")
        print(f"Documents Processed: {sync_data.get('documents_processed')}")
        print(f"Documents Added: {sync_data.get('documents_added')}")
        print(f"Documents Updated: {sync_data.get('documents_updated')}")
    
    print("\n4️⃣ Sync Statistics")
    print("-" * 30)
    
    # Get sync statistics
    stats = await sync_manager.get_sync_statistics()
    print(f"Status: {stats.get('status')}")
    if stats.get('status') == 'success':
        data = stats.get('data', {})
        print(f"Sync History File: {data.get('sync_history_file')}")
        
        # Show source statistics
        source_stats = data.get('source_statistics', {})
        for source_name, source_data in source_stats.items():
            if source_data.get('enabled'):
                print(f"  {source_name}:")
                print(f"    Last Sync: {source_data.get('last_sync')}")
                print(f"    Strategy: {source_data.get('last_sync_strategy')}")
                print(f"    Status: {source_data.get('sync_status')}")
                print(f"    Documents: {source_data.get('documents_processed')} processed, {source_data.get('documents_added')} added, {source_data.get('documents_updated')} updated")
        
        # Show overall statistics
        overall_stats = data.get('overall_statistics', {})
        print(f"\nOverall Statistics:")
        print(f"  Sources Enabled: {overall_stats.get('total_sources_enabled')}")
        print(f"  Sources Synced: {overall_stats.get('total_sources_synced')}")
        print(f"  Total Documents: {overall_stats.get('total_documents_processed')} processed, {overall_stats.get('total_documents_added')} added, {overall_stats.get('total_documents_updated')} updated")
        
        # Show efficiency metrics
        efficiency = overall_stats.get('sync_efficiency', {})
        print(f"  Efficiency:")
        print(f"    New Documents Rate: {efficiency.get('new_documents_rate', 0):.1f}%")
        print(f"    Update Rate: {efficiency.get('update_rate', 0):.1f}%")
        print(f"    Deletion Rate: {efficiency.get('deletion_rate', 0):.1f}%")
    
    print("\n5️⃣ Sync Status")
    print("-" * 30)
    
    # Get sync status
    status = await sync_manager.get_sync_status()
    print(f"Status: {status.get('status')}")
    if status.get('status') == 'success':
        data = status.get('data', {})
        for source_name, source_data in data.items():
            if source_data.get('enabled'):
                print(f"  {source_name}: {source_data.get('status')} (Last: {source_data.get('last_sync')})")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_incremental_sync())
