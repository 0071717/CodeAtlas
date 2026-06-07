type PropertySearchFilters = {
  location: string;
  minBedrooms: number;
};

export function usePropertySearchQuery(filters: PropertySearchFilters) {
  const params = new URLSearchParams({
    location: filters.location,
    min_bedrooms: String(filters.minBedrooms),
  });

  return { data: `/properties/search?${params.toString()}`, isLoading: false };
}
