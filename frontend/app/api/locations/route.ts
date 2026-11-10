import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q');
  if (!q || q.length < 3) return NextResponse.json([]);

  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=jsonv2&addressdetails=1&limit=5&accept-language=en&featuretype=city&dedupe=1`,
      {
        headers: {
          'User-Agent': 'ThankMeLater-Dev/1.0'
        }
      }
    );

    if (!response.ok) {
      throw new Error(`Geocoding API returned status ${response.status}`);
    }

    const data = await response.json();

    const normalized = data
      .filter((item: any) => item.addresstype === 'city' || item.addresstype === 'town' || item.addresstype === 'municipality')
      .map((item: any) => {
        const city = item.address?.city || item.address?.town || item.address?.village || '';
        const state = item.address?.state || '';
        const country = item.address?.country || '';
        return {
          display_name: `${city}${state ? ', ' + state : ''}, ${country}`,
          city,
          state,
          country,
          country_code: (item.address?.country_code || '').toUpperCase(),
          latitude: parseFloat(item.lat),
          longitude: parseFloat(item.lon),
          location_type: 'city'
        };
      });

    return NextResponse.json(normalized);
  } catch (e) {
    console.error('Geocoding error:', e);
    return NextResponse.json({ error: 'Geocoding failed' }, { status: 500 });
  }
}