import axios from "axios";
import {ElMessage} from "element-plus";

const huhAxios = axios.create({
    baseURL: 'http://localhost:8001/',
    timeout: 6666,
});

// 请求拦截
huhAxios.interceptors.request.use(
    config => {
        return config;
    },
    error => {
        ElMessage.error("请求失败")
        return Promise.reject(error);
    }
);

// 响应拦截
huhAxios.interceptors.response.use(
    response => {
        return response.data;
    },
    error => {
        ElMessage.error("服务器发生异常")
        return Promise.reject(error);
    }
);

export default huhAxios;