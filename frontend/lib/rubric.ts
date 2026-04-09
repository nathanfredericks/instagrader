import type { Rubric } from "@/lib/types";

export type LevelLookup = {
  score: number;
  descriptor: string;
};

export type CriterionLookup = {
  name: string;
  order: number;
  levels: Map<string, LevelLookup>;
};

// nested map for O(1) criterion/level lookups during score rendering
export function buildRubricLookup(rubric: Rubric): Map<string, CriterionLookup> {
  const map = new Map<string, CriterionLookup>();

  for (const criterion of rubric.criteria) {
    const levels = new Map<string, LevelLookup>();
    for (const level of criterion.levels) {
      levels.set(level.id, { score: level.score, descriptor: level.descriptor });
    }
    map.set(criterion.id, {
      name: criterion.name,
      order: criterion.order ?? 0,
      levels,
    });
  }

  return map;
}
