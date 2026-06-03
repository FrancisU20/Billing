import { z } from "zod";

export const offsetListResponseSchema = <TItem extends z.ZodTypeAny>(itemSchema: TItem) =>
  z.object({
    items: z.array(itemSchema),
    total: z.number().int().nonnegative(),
    offset: z.number().int().nonnegative(),
    limit: z.number().int().positive(),
  });

export const downloadUrlResponseSchema = z.object({
  url: z.string().url(),
  expires_in: z.number().int().positive(),
});

export type DownloadUrlResponse = z.infer<typeof downloadUrlResponseSchema>;
