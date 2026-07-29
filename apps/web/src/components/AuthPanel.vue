<script setup lang="ts">
import { computed, ref } from "vue";

import { AuthApiClient, type AuthUser } from "../api/auth";
import type { Locale } from "../i18n";

const props = defineProps<{ locale: Locale }>();
const emit = defineEmits<{ authenticated: [user: AuthUser] }>();

const mode = ref<"login" | "register">("login");
const displayName = ref("");
const email = ref("");
const password = ref("");
const pending = ref(false);
const requestSent = ref(false);
const error = ref("");
const client = new AuthApiClient();
const isFrench = computed(() => props.locale === "fr");

function changeMode(nextMode: "login" | "register"): void {
  mode.value = nextMode;
  error.value = "";
  password.value = "";
}

async function submit(): Promise<void> {
  if (pending.value) return;
  error.value = "";
  if (mode.value === "register" && displayName.value.trim().length < 2) {
    error.value = isFrench.value ? "Le nom doit contenir au moins 2 caractères." : "Name must contain at least 2 characters.";
    return;
  }
  if (password.value.length < 10) {
    error.value = isFrench.value ? "Le mot de passe doit contenir au moins 10 caractères." : "Password must contain at least 10 characters.";
    return;
  }
  pending.value = true;
  try {
    if (mode.value === "register") {
      await client.register(displayName.value, email.value, password.value);
      requestSent.value = true;
      password.value = "";
      return;
    }
    const user = await client.login(email.value, password.value);
    password.value = "";
    emit("authenticated", user);
  } catch (reason) {
    const message = reason instanceof Error ? reason.message : "Account request failed";
    error.value = isFrench.value
      ? message
        .replace("Invalid email or password", "E-mail ou mot de passe incorrect.")
        .replace("An account already exists for this email", "Un compte existe déjà pour cet e-mail.")
        .replace("Enter a valid email address", "Saisissez une adresse e-mail valide.")
        .replace("Account is awaiting administrator approval", "Votre demande attend la validation d’un administrateur.")
        .replace("Account request was rejected", "Votre demande de compte a été refusée.")
      : message;
    password.value = "";
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-panel panel">
      <div class="auth-visual" aria-hidden="true">
        <div class="identity-orbit"><i></i><i></i><b>OM</b></div>
        <div class="identity-lines"><i v-for="index in 12" :key="index"></i></div>
      </div>
      <div class="auth-form-wrap">
        <p class="eyebrow">{{ isFrench ? "ESPACE PERSONNEL" : "PERSONAL WORKSPACE" }}</p>
        <h1>{{ mode === "login" ? (isFrench ? "Bon retour." : "Welcome back.") : (isFrench ? "Créez votre studio." : "Create your studio.") }}</h1>
        <p>{{ isFrench
          ? "Vos sources, réglages et masters restent isolés dans votre compte."
          : "Your sources, settings, and masters remain isolated inside your account."
        }}</p>
        <div v-if="requestSent" class="account-request-sent" role="status">
          <span>✓</span>
          <h2>{{ isFrench ? "Demande envoyée" : "Request sent" }}</h2>
          <p>{{ isFrench
            ? "Un administrateur doit valider votre compte avant votre première connexion."
            : "An administrator must approve your account before your first sign-in."
          }}</p>
          <button type="button" @click="requestSent = false; changeMode('login')">
            {{ isFrench ? "Revenir à la connexion" : "Return to sign in" }}
          </button>
        </div>
        <div v-if="!requestSent" class="auth-tabs">
          <button type="button" :class="{ active: mode === 'login' }" @click="changeMode('login')">
            {{ isFrench ? "Connexion" : "Sign in" }}
          </button>
          <button type="button" :class="{ active: mode === 'register' }" @click="changeMode('register')">
            {{ isFrench ? "Créer un compte" : "Create account" }}
          </button>
        </div>
        <form v-if="!requestSent" @submit.prevent="submit">
          <label v-if="mode === 'register'">
            <span>{{ isFrench ? "Nom affiché" : "Display name" }}</span>
            <input v-model.trim="displayName" name="name" autocomplete="name" maxlength="80" required />
          </label>
          <label>
            <span>E-mail</span>
            <input v-model.trim="email" name="email" type="email" autocomplete="email" maxlength="320" required />
          </label>
          <label>
            <span>{{ isFrench ? "Mot de passe" : "Password" }}</span>
            <input
              v-model="password"
              name="password"
              type="password"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              minlength="10"
              maxlength="128"
              required
            />
            <small v-if="mode === 'register'">{{ isFrench ? "10 caractères minimum" : "10 characters minimum" }}</small>
          </label>
          <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
          <button class="master-button" type="submit" :disabled="pending">
            <span>{{ pending
              ? (isFrench ? "Vérification…" : "Checking…")
              : mode === "login"
                ? (isFrench ? "Entrer dans le studio" : "Enter the studio")
                : (isFrench ? "Créer mon espace" : "Create my workspace")
            }}</span>
            <b>→</b>
          </button>
        </form>
        <p class="auth-security">● {{ isFrench
          ? "Session HttpOnly · mot de passe salé PBKDF2 · projets privés"
          : "HttpOnly session · salted PBKDF2 password · private projects"
        }}</p>
      </div>
    </section>
  </main>
</template>
