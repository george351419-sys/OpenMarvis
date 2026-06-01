export const CARD_TYPES = {
  FILE_LIST: "mv-file-list",
  IMAGE_GALLERY: "mv-image-gallery",
  VIDEO: "mv-video-card",
  DELETE_LIST: "mv-delete-list",
  PRODUCT: "mv-product",
  TOOL_CALL: "mv-tool-call",
  APP_LIST: "mv-app-list",
  ASK_USER: "mv-ask-user",
} as const;

export type CardType = (typeof CARD_TYPES)[keyof typeof CARD_TYPES];
