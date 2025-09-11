<template>
    <div class="sidebar">
        <el-menu
            default-active="1"
            class="sidebar-el-menu"
            @open="handleOpen"
            @close="handleClose"
            :router = "true"
        >
            <el-menu-item index="/pdf-upload">
            <el-icon><DataBoard /></el-icon>
            <span>文件管理</span>
            </el-menu-item>

            <el-menu-item index="/parse">
            <el-icon><Collection /></el-icon>
            <span>文件解析</span>
            </el-menu-item>

            <el-menu-item index="/build">
            <el-icon><DocumentAdd/></el-icon>
            <span>图谱构建</span>
            </el-menu-item>

            <el-menu-item index="/QA">
            <el-icon><Search /></el-icon>
            <span>知识问答</span>
            </el-menu-item>


        </el-menu>
    </div>
</template>

<script lang="ts" setup>
import {
DataBoard,
DocumentAdd,
Menu as IconMenu,
Location,
Setting,
DArrowRight,
Collection,
Search
} from '@element-plus/icons-vue'

const handleOpen = (key: string, keyPath: string[]) => {
console.log(key, keyPath)
}
const handleClose = (key: string, keyPath: string[]) => {
console.log(key, keyPath)
}
</script>

<style scoped>
.sidebar {
    display: block;
    overflow-y: scroll;
    height: 100%;
}
.sidebar::-webkit-scrollbar {
    width: 0;
}
.sidebar-el-menu:not(.el-menu--collapse) {
    width: 250px;
}
.sidebar > ul {
    height: 100%;
}
</style>
  