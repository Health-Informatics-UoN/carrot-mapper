// This API route handler is a simple proxy endpoint for the concept recommendation service. Here's what it does:
// - Extracts the code parameter from the request URL query string
// - Checks if the code parameter is present
// - Calls the getConceptRecommendations function with the provided code

import { NextResponse } from 'next/server';
import { getConceptRecommendations } from '@/lib/api/recommendations';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { code } = body;
    
    if (!code) {
      return NextResponse.json({ error: "Code parameter is required" }, { status: 400 });
    }
    
    const recommendations = await getConceptRecommendations(code);
    return NextResponse.json(recommendations);
  } catch (error) {
    console.error('Error in test endpoint:', error);
    return NextResponse.json({ error: "Failed to fetch recommendations" }, { status: 500 });
  }
}