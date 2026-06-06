import { AskUserCard } from "./AskUserCard";
import { DeleteListCard } from "./DeleteListCard";
import { DeletionPreviewCard } from "./DeletionPreviewCard";
import { FileListCard } from "./FileListCard";
import { ImageGalleryCard } from "./ImageGalleryCard";
import { ProductCard } from "./ProductCard";
import { SkillCallCard } from "./SkillCallCard";
import { ToolCallCard } from "./ToolCallCard";
import { VideoCard } from "./VideoCard";

export const CARD_RENDERERS = {
  "mv-file-list": FileListCard,
  "mv-image-gallery": ImageGalleryCard,
  "mv-video-card": VideoCard,
  "mv-delete-list": DeleteListCard,
  "deletion_preview": DeletionPreviewCard,
  "mv-product": ProductCard,
  "mv-tool-call": ToolCallCard,
  "mv-ask-user": AskUserCard,
  "mv-skill-call": SkillCallCard,
} as const;

export type CardKey = keyof typeof CARD_RENDERERS;
