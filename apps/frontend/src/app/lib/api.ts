const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  "https://exclusivity-backend.onrender.com";

export async function fetchOnboardingStatus() {
  const res = await fetch(`${API_BASE}/onboarding/status`, {
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error("Failed to fetch onboarding status");
  }

  return res.json();
}

export async function completeOnboarding() {
  const res = await fetch(`${API_BASE}/onboarding/complete`, {
    method: "POST",
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error("Failed to complete onboarding");
  }

  return res.json();
}
