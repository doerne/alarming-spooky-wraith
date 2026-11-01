import { useState } from "react";

import type { Source } from "../model/types";
import { useRemoveSourceApiKey, useSetSourceApiKey } from "./use-sources";

/** Zustand des Key-Dialogs: welche Quelle bearbeitet wird, Speichern, Entfernen, Fehler. */
export function useApiKeyEditing(sources: Source[] | undefined) {
  const setApiKey = useSetSourceApiKey();
  const removeApiKey = useRemoveSourceApiKey();
  const [editingKey, setEditingKey] = useState<string | null>(null);

  const close = () => {
    setApiKey.reset();
    removeApiKey.reset();
    setEditingKey(null);
  };
  const save = (apiKey: string) => {
    if (editingKey) setApiKey.mutate({ key: editingKey, apiKey }, { onSuccess: close });
  };
  const remove = () => {
    if (editingKey) removeApiKey.mutate(editingKey, { onSuccess: close });
  };
  const error = setApiKey.error ?? removeApiKey.error;

  return {
    editing: sources?.find((source) => source.key === editingKey) ?? null,
    error: error ? error.message : null,
    open: setEditingKey,
    save,
    remove,
    close,
  };
}
