import { notFound } from 'next/navigation';
import fs from 'fs';
import path from 'path';
import RoadmapClient from './RoadmapClient';

interface Link {
  title: string;
  url: string;
  type: string;
}

interface RoadmapItem {
  title: string;
  description: string;
  links: Link[];
}

interface RoadmapData {
  [key: string]: RoadmapItem;
}

async function getRoadmapData(role: string): Promise<RoadmapData | null> {
  const roleToFileMap: { [key: string]: string } = {
    "data-scientist": "ai-ds.json",
    "frontend-developer": "frontend.json",
    "backend-developer": "backend.json",
    "fullstack-developer": "full-stack.json",
    "devops-engineer": "devops.json",
    "qa-engineer": "qa.json",
    "product-manager": "product-manager.json",
    "ui-ux-designer": "ux-design.json",
    "data-analyst": "data-analyst.json"
  };

  const fileName = roleToFileMap[role];

  if (!fileName) {
    return null;
  }

  const filePath = path.join(process.cwd(), 'public', 'data', fileName);
  const fileContents = fs.readFileSync(filePath, 'utf8');
  return JSON.parse(fileContents);
}

export default async function RoadmapPage({ params }: { params: { role: string } }) {
  const { role } = params;
  const roadmapData = await getRoadmapData(role);

  if (!roadmapData) {
    notFound();
  }

  return <RoadmapClient roadmapData={roadmapData} role={role} />;
}

export async function generateStaticParams() {
  return [
    { role: "data-scientist" },
    { role: "frontend-developer" },
    { role: "backend-developer" },
    { role: "fullstack-developer" },
    { role: "devops-engineer" },
    { role: "qa-engineer" },
    { role: "product-manager" },
    { role: "ui-ux-designer" },
    { role: "data-analyst" },
  ];
}