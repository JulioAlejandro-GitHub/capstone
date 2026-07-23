export const DATASET_IMAGE_PAGE_SIZES = [12, 24, 48, 96] as const;
export const DEFAULT_DATASET_IMAGE_PAGE_SIZE = 12;

export type DatasetImagePageSize = (typeof DATASET_IMAGE_PAGE_SIZES)[number];

export function normalizeDatasetImagePageSize(value: unknown): DatasetImagePageSize {
  const parsed = Number(value);
  return DATASET_IMAGE_PAGE_SIZES.includes(parsed as DatasetImagePageSize)
    ? (parsed as DatasetImagePageSize)
    : DEFAULT_DATASET_IMAGE_PAGE_SIZE;
}
