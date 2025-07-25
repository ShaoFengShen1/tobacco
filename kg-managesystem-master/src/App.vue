<script setup>
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { ref } from "vue";
import AsideNav from "@/components/asideNav.vue";
import { Fold, Expand } from '@element-plus/icons-vue';

const locale = ref(zhCn);
const isCollapse = ref(false); // 控制侧边栏折叠状态
const asideWidth = ref('270px'); // 动态侧边栏宽度

// 切换折叠状态
function toggleCollapse() {
  isCollapse.value = !isCollapse.value;
  asideWidth.value = isCollapse.value ? '0px' : '270px';
}
</script>

<template>
  <el-config-provider :locale="locale">
    <el-container style="margin: 0; border: none; padding: 0;">
      <el-header class="nav-el-header">
        <span>卷烟知识图谱管理平台</span>
        <el-button
          @click="toggleCollapse"
          :icon="isCollapse ? Expand : Fold"
          circle
          style="float: right; margin-top: 12px;"
        />
      </el-header>
      <el-container>
        <!-- 侧边栏 -->
        <el-aside :width="asideWidth" style="transition: width 0.3s;">
          <aside-nav :is-collapse="isCollapse" />
        </el-aside>
        <!-- 主页面 -->
        <el-container>
          <el-main>
            <router-view />
          </el-main>
          <el-footer>
            <span style="font-size: 14px; margin-left: 40%;">
              Cig-KG Manage System ©2025 Created by HarmonyQuan
            </span>
          </el-footer>
        </el-container>
      </el-container>
    </el-container>
  </el-config-provider>
</template>

<style scoped>
html, body {
  height: 100%;
  margin: 0;
  border: 0;
  padding: 0;
}

.nav-el-header {
  line-height: 60px;
  font-size: large;
  background: linear-gradient(200deg, rgba(67, 98, 220, 0.75), rgba(10, 111, 239, 0.82));
  color: white;
  border-radius: 10px;
  transition: 0.125s ease-in-out;
  position: relative;
}
</style>