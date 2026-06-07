import { useState } from "react";
import { usePropertySearchQuery } from "./usePropertySearchQuery";

export function SearchPage() {
  const [location, setLocation] = useState("Austin");
  const [minBedrooms, setMinBedrooms] = useState(2);
  const { data, isLoading } = usePropertySearchQuery({ location, minBedrooms });

  return (
    <main>
      <input value={location} onChange={(event) => setLocation(event.target.value)} />
      <input
        type="number"
        value={minBedrooms}
        onChange={(event) => setMinBedrooms(Number(event.target.value))}
      />
      {isLoading ? <p>Loading</p> : <pre>{JSON.stringify(data, null, 2)}</pre>}
    </main>
  );
}
