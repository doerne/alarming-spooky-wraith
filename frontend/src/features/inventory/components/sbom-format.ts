const UPLOADED_AT_FORMAT = new Intl.DateTimeFormat("de-DE", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatUploadedAt(isoTimestamp: string): string {
  return UPLOADED_AT_FORMAT.format(new Date(isoTimestamp));
}
