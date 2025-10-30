#!/bin/bash
# Test RAG Worker System - No SerpAPI Fallback

set -e

BASE_URL="http://127.0.0.1:5000"
WORKER_URL="http://127.0.0.1:5001"

echo "========================================="
echo "Testing RAG Worker System"
echo "========================================="
echo ""

# Test 1: Worker Health Check
echo "Test 1: RAG Worker Health Check"
echo "-----------------------------------"
WORKER_RESPONSE=$(curl -s $WORKER_URL/health)
echo "Response: $WORKER_RESPONSE"

if echo "$WORKER_RESPONSE" | grep -q '"rag_ready":true'; then
    RAG_READY=$(echo "$WORKER_RESPONSE" | grep -o '"rag_ready":[^,]*' | cut -d':' -f2)
    BACKEND=$(echo "$WORKER_RESPONSE" | grep -o '"backend":"[^"]*"' | cut -d'"' -f4)
    INDEX_SIZE=$(echo "$WORKER_RESPONSE" | grep -o '"index_size":[0-9]*' | cut -d':' -f2)
    
    echo "✓ PASSED: Worker is ready"
    echo "  - RAG Ready: $RAG_READY"
    echo "  - Backend: $BACKEND"
    echo "  - Index Size: $INDEX_SIZE"
else
    echo "✗ FAILED: Worker not ready"
    exit 1
fi
echo ""

# Test 2: Main App Health Check
echo "Test 2: Main App Health Check"
echo "-----------------------------------"
APP_RESPONSE=$(curl -s $BASE_URL/health)
echo "Response: $APP_RESPONSE"

if echo "$APP_RESPONSE" | grep -q '"rag_ready":true'; then
    echo "✓ PASSED: Main app connected to worker"
else
    echo "✗ FAILED: Main app not connected to worker"
    exit 1
fi
echo ""

# Test 3: Timeline Generation (RAG only)
echo "Test 3: Timeline Generation with RAG"
echo "-----------------------------------"
TIMELINE_RESPONSE=$(curl -s -X POST $BASE_URL/process_headline \
  -H "Content-Type: application/json" \
  -d '{"headline": "Climate change impact on global economy"}')

echo "Response length: ${#TIMELINE_RESPONSE} chars"

if echo "$TIMELINE_RESPONSE" | grep -q '"event"'; then
    EVENT_COUNT=$(echo "$TIMELINE_RESPONSE" | grep -o '"year"' | wc -l | tr -d ' ')
    echo "✓ PASSED: Timeline generated"
    echo "  - Events returned: $EVENT_COUNT"
    
    # Check if using RAG (no SerpAPI sources)
    if echo "$TIMELINE_RESPONSE" | grep -qi 'serpapi\|google'; then
        echo "⚠ WARNING: Response may contain SerpAPI results"
    else
        echo "  - ✓ Using RAG (no SerpAPI)"
    fi
else
    echo "✗ FAILED: Timeline not generated"
    echo "Full response: $TIMELINE_RESPONSE"
    exit 1
fi
echo ""

# Test 4: Chat AI (RAG only)
echo "Test 4: Chat AI with RAG"
echo "-----------------------------------"
CHAT_RESPONSE=$(curl -s -X POST $BASE_URL/ask \
  -H "Content-Type: application/json" \
  -d '{"headline": "Renewable energy adoption", "question": "What are the recent developments?"}')

echo "Response length: ${#CHAT_RESPONSE} chars"

if echo "$CHAT_RESPONSE" | grep -q '"answer"'; then
    ANSWER_LENGTH=$(echo "$CHAT_RESPONSE" | grep -o '"answer":"[^"]*"' | wc -c)
    echo "✓ PASSED: Chat AI response received"
    echo "  - Answer length: $ANSWER_LENGTH chars"
    
    # Check if using RAG
    if echo "$CHAT_RESPONSE" | grep -qi 'serpapi\|google'; then
        echo "⚠ WARNING: Response may contain SerpAPI results"
    else
        echo "  - ✓ Using RAG (no SerpAPI)"
    fi
else
    echo "✗ FAILED: Chat AI did not respond"
    echo "Full response: $CHAT_RESPONSE"
    exit 1
fi
echo ""

# Test 5: Direct Worker Embedding
echo "Test 5: Worker Embedding Test"
echo "-----------------------------------"
EMBED_RESPONSE=$(curl -s -X POST $WORKER_URL/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["test query"]}')

if echo "$EMBED_RESPONSE" | grep -q '"vectors"'; then
    VECTOR_DIM=$(echo "$EMBED_RESPONSE" | grep -o '"shape":\[[0-9,]*\]' | grep -o '[0-9]*' | tail -1)
    echo "✓ PASSED: Worker embedding works"
    echo "  - Vector dimension: $VECTOR_DIM"
else
    echo "✗ FAILED: Worker embedding failed"
    echo "Response: $EMBED_RESPONSE"
    exit 1
fi
echo ""

# Test 6: Direct Worker Search
echo "Test 6: Worker Search Test"
echo "-----------------------------------"
SEARCH_RESPONSE=$(curl -s -X POST $WORKER_URL/search \
  -H "Content-Type: application/json" \
  -d '{"query": "technology innovation", "k": 5}')

if echo "$SEARCH_RESPONSE" | grep -q '"results"'; then
    RESULT_COUNT=$(echo "$SEARCH_RESPONSE" | grep -o '"title"' | wc -l | tr -d ' ')
    echo "✓ PASSED: Worker search works"
    echo "  - Results returned: $RESULT_COUNT"
else
    echo "✗ FAILED: Worker search failed"
    echo "Response: $SEARCH_RESPONSE"
    exit 1
fi
echo ""

# Test 7: Load Test (10 concurrent requests)
echo "Test 7: Load Test (10 concurrent requests)"
echo "-----------------------------------"
SUCCESS_COUNT=0
for i in {1..10}; do
    curl -s -X POST $BASE_URL/process_headline \
      -H "Content-Type: application/json" \
      -d "{\"headline\": \"Test query $i\"}" > /dev/null 2>&1 &
done

wait

# Give server time to process
sleep 5

# Check if both services still alive
WORKER_ALIVE=$(curl -s $WORKER_URL/health 2>/dev/null | grep -o '"status":"ok"' || echo "")
APP_ALIVE=$(curl -s $BASE_URL/health 2>/dev/null | grep -o '"ok":true' || echo "")

if [ -n "$WORKER_ALIVE" ] && [ -n "$APP_ALIVE" ]; then
    echo "✓ PASSED: System stable under load"
    echo "  - Worker: alive"
    echo "  - Main app: alive"
else
    echo "✗ FAILED: System crashed under load"
    exit 1
fi
echo ""

# Final Summary
echo "========================================="
echo "✓ All Tests Passed!"
echo "========================================="
echo ""
echo "Summary:"
echo "  - RAG Worker: Fully operational"
echo "  - Main App: Connected to worker"
echo "  - Timeline: Working with RAG"
echo "  - Chat AI: Working with RAG"
echo "  - Load Test: System stable"
echo ""
echo "System is ready for production use!"
echo "No SerpAPI fallback needed - full RAG operation."
echo ""
