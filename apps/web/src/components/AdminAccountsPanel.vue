<script setup lang="ts">
import { onMounted, ref } from "vue";

import { AuthApiClient, type AuthUser } from "../api/auth";
import type { Locale } from "../i18n";

const props = defineProps<{ locale: Locale }>();
defineEmits<{ back: [] }>();

const requests = ref<AuthUser[]>([]);
const loading = ref(true);
const error = ref("");
const reviewing = ref<string | null>(null);
const client = new AuthApiClient();
const c = (fr: string, en: string): string => props.locale === "fr" ? fr : en;

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    requests.value = await client.listRequests();
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : c("Chargement impossible", "Unable to load requests");
  } finally {
    loading.value = false;
  }
}

async function review(user: AuthUser, decision: "approve" | "reject"): Promise<void> {
  if (reviewing.value) return;
  reviewing.value = user.id;
  error.value = "";
  try {
    await client.review(user.id, decision);
    requests.value = requests.value.filter((candidate) => candidate.id !== user.id);
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : c("Action impossible", "Unable to review request");
  } finally {
    reviewing.value = null;
  }
}

onMounted(load);
</script>

<template>
  <main class="admin-page">
    <header class="admin-hero">
      <div>
        <p class="eyebrow">ADMIN · {{ c("ACCÈS", "ACCESS") }}</p>
        <h1>{{ c("Demandes de comptes.", "Account requests.") }}</h1>
        <p>{{ c(
          "Chaque inscription reste inactive jusqu’à votre décision. Aucun projet ne peut être envoyé avant validation.",
          "Every registration remains inactive until your decision. No project can be uploaded before approval.",
        ) }}</p>
      </div>
      <button type="button" @click="$emit('back')">← {{ c("Retour au studio", "Back to studio") }}</button>
    </header>

    <section class="admin-requests panel">
      <div class="panel-heading">
        <div><span class="step">{{ requests.length }}</span><h2>{{ c("En attente", "Pending") }}</h2></div>
        <button type="button" :disabled="loading" @click="load">↻ {{ c("Actualiser", "Refresh") }}</button>
      </div>
      <div v-if="loading" class="admin-empty"><i></i>{{ c("Chargement…", "Loading…") }}</div>
      <p v-else-if="error" class="auth-error" role="alert">{{ error }}</p>
      <div v-else-if="requests.length" class="request-list">
        <article v-for="request in requests" :key="request.id">
          <span class="request-avatar">{{ request.display_name.slice(0, 1).toUpperCase() }}</span>
          <div>
            <strong>{{ request.display_name }}</strong>
            <small>{{ request.email }}</small>
            <time v-if="request.created_at">{{ new Date(request.created_at).toLocaleString(locale) }}</time>
          </div>
          <div class="request-actions">
            <button type="button" :disabled="reviewing !== null" @click="review(request, 'reject')">
              × {{ c("Refuser", "Reject") }}
            </button>
            <button type="button" :disabled="reviewing !== null" @click="review(request, 'approve')">
              ✓ {{ c("Valider", "Approve") }}
            </button>
          </div>
        </article>
      </div>
      <div v-else class="admin-empty"><span>✓</span>{{ c("Aucune demande en attente", "No pending requests") }}</div>
    </section>
  </main>
</template>
