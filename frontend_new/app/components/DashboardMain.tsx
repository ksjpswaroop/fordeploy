"use client";
// Reused core dashboard logic extracted from original dashboard/page.tsx
import React from 'react';
import DashboardPage from '../dashboard/page';

// For now we simply re-export existing page contents to minimize refactor risk.
// Later we could move the content here directly; this wrapper allows reuse inside Candidate flow.
export default function DashboardMain(){
  return <DashboardPage />;
}
