import { useMutation } from '@tanstack/vue-query';
import { api } from 'src/boot/axios';
import { useUserStore } from 'src/stores/user.store';
import { jwtDecode } from 'jwt-decode';

type LoginParams = {
  username: string;
  password: string;
};

export const useLoginQuery = () => {
  const { setAccessToken, setUsername, setUserAuthorization } = useUserStore();

  const handleLogin = async (params: LoginParams) => {
    const { data } = await api.post<{ access: string }>('token/obtain/', params);
    api.defaults.headers.common.Authorization = `Bearer ${data.access}`;
    setAccessToken(data.access);
    setUsername(params.username);
    setUserAuthorization(jwtDecode<{ machineTurn: string }>(data.access).machineTurn);
    return data;
  };

  const { mutate, isPending } = useMutation({
    mutationFn: handleLogin,
  });

  return {
    login: mutate,
    isLoadingLogin: isPending,
  };
};
