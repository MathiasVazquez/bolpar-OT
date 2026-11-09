<template>
  <q-page class="login-page">
    <q-card flat bordered class="login-card">
      <q-card-section>
        <div class="text-h6 text-weight-bold text-center">
          Iniciar sesión
        </div>
      </q-card-section>

      <q-card-section>
        <q-form @submit="onConfirmLogin" class="column gap-md">
          <q-input
            v-model="loginCredentials.username"
            outlined
            dense
            type="text"
            label="Nombre de usuario"
            :rules="[(val) => !!val || 'Campo requerido']"
            class="full-width"
            :disable="isLoadingLogin"
          />

          <q-input
            v-model="loginCredentials.password"
            outlined
            dense
            type="password"
            label="Contraseña"
            :rules="[(val) => !!val || 'Campo requerido']"
            class="full-width"
            :disable="isLoadingLogin"
          />

          <q-btn
            unelevated
            no-caps
            label="Ingresar"
            type="submit"
            color="primary"
            class="full-width"
            :loading="isLoadingLogin"
          />
        </q-form>
      </q-card-section>

      <q-card-section class="text-center q-pt-none">
        <div class="text-caption">Versión {{ version }}</div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useLoginQuery } from 'src/queries/login-query';
import { version } from '../../package.json';

const { login, isLoadingLogin } = useLoginQuery();

const loginCredentials = reactive({
  username: '',
  password: '',
});

const onConfirmLogin = () => {
  login(loginCredentials);
};
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.login-card {
  width: min(360px, 100%);
  border-radius: 12px;
}
</style>