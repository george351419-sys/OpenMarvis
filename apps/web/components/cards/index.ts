import { AskUserCard } from "./AskUserCard";
import { DeleteListCard } from "./DeleteListCard";
import { FileListCard } from "./FileListCard";
import { ImageGalleryCard } from "./ImageGalleryCard";
import { ProductCard } from "./ProductCard";
import { ToolCallCard } from "./ToolCallCard";
import { VideoCard } from "./VideoCard";

export const CARD_RENDERERS = {
  "mv-file-list": FileListCard,
  "mv-image-gallery": ImageGalleryCard,
  "mv-video-card": VideoCard,
  "mv-delete-list": DeleteListCard,
  "mv-product": ProductCard,
  "mv-tool-call": ToolCallCard,
  "mv-ask-user": AskUserCard,
} as const;

export type CardKey = keyof typeof CARD_RENDERERS;
