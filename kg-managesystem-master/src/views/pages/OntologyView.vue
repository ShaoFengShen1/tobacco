<template>
  <div class="ontology-container">
    <div class="header">
      <h2>本体管理</h2>
      <el-button type="primary" @click="showCreateDialog" :icon="Plus">新建本体</el-button>
    </div>

    <el-card class="box-card">
      <el-table :data="ontologyList" style="width: 100%" stripe>
        <el-table-column prop="name" label="本体文档名" width="200">
          <template #default="scope">
            <el-input
              v-if="scope.row.isEditing"
              v-model="scope.row.editName"
              @blur="saveEdit(scope.row)"
              size="small"
            />
            <span v-else class="ontology-name">{{ scope.row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="文档描述" min-width="250">
          <template #default="scope">
            <el-input
              v-if="scope.row.isEditing"
              v-model="scope.row.editDescription"
              type="textarea"
              autosize
              @blur="saveEdit(scope.row)"
              size="small"
            />
            <span v-else class="ontology-description">{{ scope.row.description }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="updateTime" label="修改时间" width="180" sortable />
        <el-table-column label="包含实体" width="220">
          <template #default="scope">
            <el-scrollbar max-height="60px">
              <el-tag
                v-for="entity in scope.row.entities"
                :key="entity"
                type="success"
                effect="light"
                style="margin: 2px;"
              >
                {{ entity }}
              </el-tag>
            </el-scrollbar>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right" align="center">
          <template #default="scope">
            <el-button
              size="small"
              @click="toggleEdit(scope.row)"
              :type="scope.row.isEditing ? 'info' : 'default'"
              plain
            >
              {{ scope.row.isEditing ? '取消' : '编辑元数据' }}
            </el-button>
             <el-button
              size="small"
              type="primary"
              @click="handleEdit(scope.row)"
              :icon="Edit"
            >
              设计
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(scope.row)"
              :icon="Delete"
              circle
              plain
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="新建本体" width="400px" center>
      <el-form :model="newOntology" label-width="80px">
        <el-form-item label="文档名">
          <el-input v-model="newOntology.name" placeholder="例如：人物关系本体" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newOntology.description" type="textarea" placeholder="对这个本体的简短描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="createOntology">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" :title="`设计本体 - ${editingOntology.name}`" fullscreen destroy-on-close>
      <div class="edit-container">
        <div class="mode-switch">
           <el-text size="large" tag="b">设计模式：</el-text>
          <el-button-group>
            <el-button :type="mode === 'table' ? 'primary' : 'default'" @click="mode = 'table'" :icon="Grid">表格模式</el-button>
            <el-button :type="mode === 'canvas' ? 'primary' : 'default'" @click="mode = 'canvas'" :icon="Picture">画板模式</el-button>
          </el-button-group>
        </div>

        <div v-if="mode === 'table'" class="table-mode">
          <el-card class="box-card entity-section">
             <template #header>
                <div class="card-header">
                  <h3>实体管理 (Entity)</h3>
                  <el-button type="primary" @click="showCreateEntityDialog" :icon="Plus">新建实体</el-button>
                </div>
              </template>
            <el-table :data="entities" style="width: 100%" stripe border>
              <el-table-column prop="name" label="实体名称" width="180" />
              <el-table-column prop="label" label="类标签" width="180" />
              <el-table-column prop="definition" label="定义" min-width="200" />
              <el-table-column label="属性 (Properties)">
                <template #default="scope">
                  <el-tag
                    v-for="(property, index) in scope.row.properties"
                    :key="index"
                    type="info"
                    style="margin: 2px;"
                  >
                    {{ property }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="实例 (Instances)">
                <template #default="scope">
                   <el-tag
                    v-for="(instance, index) in scope.row.instances"
                    :key="index"
                    style="margin: 2px;"
                  >
                    {{ instance }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="180" align="center">
                <template #default="scope">
                  <el-button size="small" @click="editEntity(scope.row)" :icon="Edit" text bg>编辑</el-button>
                  <el-button size="small" type="danger" @click="deleteEntity(scope.row)" :icon="Delete" text bg>删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card class="box-card relation-section">
             <template #header>
                <div class="card-header">
                  <h3>关系管理 (Relation)</h3>
                  <el-button type="primary" @click="showCreateRelationDialog" :icon="Plus">新建关系</el-button>
                </div>
              </template>
            <el-table :data="relations" style="width: 100%" stripe border>
              <el-table-column prop="name" label="关系名称" width="180" />
              <el-table-column prop="label" label="关系标签" width="180" />
              <el-table-column prop="from" label="头实体 (Domain)" width="180" />
              <el-table-column prop="to" label="尾实体 (Range)" width="180" />
              <el-table-column prop="definition" label="定义" min-width="200" />
              <el-table-column label="操作" width="180" align="center">
                <template #default="scope">
                  <el-button size="small" @click="editRelation(scope.row)" :icon="Edit" text bg>编辑</el-button>
                  <el-button size="small" type="danger" @click="deleteRelation(scope.row)" :icon="Delete" text bg>删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>

        <div v-if="mode === 'canvas'" class="canvas-mode">
          <div id="ontology-canvas" ref="canvas"></div>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="entityDialogVisible" :title="`${isEditingEntity ? '编辑' : '新建'}实体`" width="600px">
      <el-form :model="currentEntity" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="currentEntity.name" placeholder="实体类名称，必填项"/>
        </el-form-item>
        <el-form-item label="类标签">
          <el-input v-model="currentEntity.label" placeholder="实体类英文标签，选填项"/>
        </el-form-item>
        <el-form-item label="定义">
          <el-input v-model="currentEntity.definition" type="textarea" placeholder="实体类说明，选填项"/>
        </el-form-item>
        <el-form-item label="属性">
          <div v-for="(property, index) in currentEntity.properties" :key="index" class="property-item">
            <el-input
              v-model="currentEntity.properties[index]"
              placeholder="属性名称"
              style="flex: 1;"
              :disabled="index === 0"
            />
            <el-button
              type="danger"
              @click="removeProperty(index)"
              :disabled="index === 0"
              circle
              :icon="Delete"
              plain
            />
          </div>
          <el-button @click="addProperty" class="add-button" :icon="Plus" plain>添加属性</el-button>
        </el-form-item>
        <el-form-item label="实例">
          <div v-for="(instance, index) in currentEntity.instances" :key="index" class="instance-item">
            <el-input v-model="currentEntity.instances[index]" placeholder="实例名称" style="flex: 1;" />
            <el-button type="danger" @click="removeInstance(index)" circle :icon="Delete" plain />
          </div>
          <el-button @click="addInstance" class="add-button" :icon="Plus" plain>添加实例</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="entityDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEntity">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="relationDialogVisible" :title="`${isEditingRelation ? '编辑' : '新建'}关系`" width="600px">
      <el-form :model="currentRelation" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="currentRelation.name" placeholder="关系名称，必填项"/>
        </el-form-item>
        <el-form-item label="关系标签">
          <el-input v-model="currentRelation.label" placeholder="关系英文标签，选填项"/>
        </el-form-item>
        <el-form-item label="头实体">
          <el-select v-model="currentRelation.from" placeholder="请选择头实体" style="width: 100%;">
            <el-option
              v-for="entity in entities"
              :key="entity.name"
              :label="entity.name"
              :value="entity.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="尾实体">
          <el-select v-model="currentRelation.to" placeholder="请选择尾实体" style="width: 100%;">
            <el-option
              v-for="entity in entities"
              :key="entity.name"
              :label="entity.name"
              :value="entity.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="定义">
          <el-input v-model="currentRelation.definition" type="textarea" placeholder="关系说明，选填项"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="relationDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRelation">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
// --- SCRIPT部分是最终版, 无需改动 ---
import {ref, onMounted, watch, nextTick} from 'vue'
import * as d3 from 'd3'
import neo4j from 'neo4j-driver'
import { ElMessage } from 'element-plus'
import moment from 'moment'
import { Plus, Edit, Delete, Grid, Picture } from '@element-plus/icons-vue'

export default {
  name: "Ontology",
  setup() {
    const neo4jUri = 'bolt://localhost:7687'
    const neo4jUser = 'neo4j'
    const neo4jPassword = '12345678'
    const driver = neo4j.driver(neo4jUri, neo4j.auth.basic(neo4jUser, neo4jPassword))
    const database_name = 'ontology'
    const ontologyList = ref([])

    const loadOntologies = async () => {
      const session = driver.session({ database: database_name })
      try {
        const result = await session.run(
          `MATCH (o:Ontology)
           OPTIONAL MATCH (e:Entity)-[:BELONGS_TO]->(o)
           RETURN o.id as id, o.name as name, o.description as description,
                  o.updateTime as updateTime, COLLECT(DISTINCT e.name) as entities`
        )
        ontologyList.value = result.records.map(record => ({
          id: record.get('id'),
          name: record.get('name'),
          description: record.get('description'),
          updateTime: formatBeijingTime(record.get('updateTime')),
          entities: record.get('entities') || [],
          isEditing: false,
          editName: record.get('name'),
          editDescription: record.get('description')
        }))
      } catch (error) {
        console.error('Error loading ontologies:', error)
        ElMessage.error('加载本体列表失败')
      } finally {
        session.close()
      }
    }

    const toggleEdit = (row) => {
      if (row.isEditing) {
        row.editName = row.name
        row.editDescription = row.description
      }
      row.isEditing = !row.isEditing
    }

    const saveEdit = async (row) => {
      if (!row.editName.trim()) {
        ElMessage.error('本体名称不能为空')
        row.isEditing = true
        return
      }
      const session = driver.session({ database: database_name })
      try {
        await session.run(
          `MATCH (o:Ontology {id: $id})
           SET o.name = $name,
               o.description = $description,
               o.updateTime = toString(datetime())`,
          {
            id: row.id,
            name: row.editName,
            description: row.editDescription
          }
        )
        row.name = row.editName
        row.description = row.editDescription
        row.isEditing = false
        ElMessage.success('本体信息更新成功')
      } catch (error) {
        console.error('Error updating ontology:', error)
        ElMessage.error('更新本体信息失败')
      } finally {
        session.close()
      }
    }

    const formatBeijingTime = (date) => {
      if (!date) return '-'
      return moment(date).utcOffset(8).format('YYYY-MM-DD HH:mm:ss')
    }

    const createDialogVisible = ref(false)
    const newOntology = ref({ name: '', description: '' })

    const createOntology = async () => {
      if (!newOntology.value.name) {
        ElMessage.error('本体名称不能为空')
        return
      }
      const session = driver.session({ database: database_name })
      try {
        await session.run(
          `CREATE (o:Ontology {
            id: apoc.create.uuid(),
            name: $name,
            description: $description,
            updateTime: toString(datetime())
          }) RETURN o`,
          {
            name: newOntology.value.name,
            description: newOntology.value.description
          }
        )
        ElMessage.success('本体创建成功')
        await loadOntologies()
        createDialogVisible.value = false
      } catch (error) {
        console.error('Error creating ontology:', error)
        ElMessage.error('创建本体失败')
      } finally {
        session.close()
      }
    }

    const editDialogVisible = ref(false)
    const editingOntology = ref({})
    const mode = ref('table')
    const entities = ref([])
    const relations = ref([])

    const handleEdit = async (ontology) => {
      editingOntology.value = ontology
      mode.value = 'table'
      const entitiesSession = driver.session({ database: database_name })
      try {
        const entitiesResult = await entitiesSession.run(
          `MATCH (e:Entity)-[:BELONGS_TO]->(o:Ontology {id: $id})
           RETURN e.id as id, e.name as name, e.label as label, e.definition as definition`,
          { id: ontology.id }
        )
        entities.value = await Promise.all(entitiesResult.records.map(async record => {
          const propertySession = driver.session({ database: database_name })
          const instanceSession = driver.session({ database: database_name })
          try {
            const propertiesResult = await propertySession.run(
              `MATCH (e:Entity {id: $entityId})-[:HAS_PROPERTY]->(p:Property)
               RETURN p.name as name`,
              { entityId: record.get('id') }
            )
            const instancesResult = await instanceSession.run(
              `MATCH (e:Entity {id: $entityId})-[:HAS_INSTANCE]->(i:Instance)
               RETURN i.name as name`,
              { entityId: record.get('id') }
            )
            return {
              id: record.get('id'),
              name: record.get('name'),
              label: record.get('label'),
              definition: record.get('definition'),
              properties: propertiesResult.records.map(p => p.get('name')),
              instances: instancesResult.records.map(i => i.get('name'))
            }
          } finally {
            propertySession.close()
            instanceSession.close()
          }
        }))

        const relationsSession = driver.session({ database: database_name })
        try {
          const relationsResult = await relationsSession.run(
            `MATCH (from:Entity)-[r:RELATION]->(to:Entity)
             WHERE (from)-[:BELONGS_TO]->(:Ontology {id: $id}) AND (to)-[:BELONGS_TO]->(:Ontology {id: $id})
             RETURN r.id as id, r.name as name, r.label as label, r.definition as definition,
                    from.name as from, to.name as to`,
            { id: ontology.id }
          )
          relations.value = relationsResult.records.map(record => ({
            id: record.get('id'),
            name: record.get('name'),
            label: record.get('label'),
            definition: record.get('definition'),
            from: record.get('from'),
            to: record.get('to')
          }))
        } finally {
          relationsSession.close()
        }
        editDialogVisible.value = true
      } catch (error) {
        console.error('Error loading ontology details:', error)
        ElMessage.error('加载本体详情失败: ' + error.message)
      } finally {
        entitiesSession.close()
      }
    }

    const handleDelete = async (ontology) => {
      const session = driver.session({ database: database_name })
      try {
        await session.run( `MATCH (o:Ontology {id: $id}) DETACH DELETE o`, { id: ontology.id } )
        ElMessage.success('本体删除成功')
        loadOntologies()
      } catch (error) {
        console.error('Error deleting ontology:', error)
        ElMessage.error('删除本体失败')
      } finally {
        session.close()
      }
    }

    const entityDialogVisible = ref(false)
    const isEditingEntity = ref(false)
    const currentEntity = ref({ name: '', label: '', definition: '', properties: [], instances: [] })

    const addInstance = () => { currentEntity.value.instances.push('') }
    const removeInstance = (index) => { currentEntity.value.instances.splice(index, 1) }

    const saveEntity = async () => {
      if (!currentEntity.value.name.trim()) { ElMessage.error('实体名称不能为空'); return }
      for (const property of currentEntity.value.properties) {
        if (!property.trim()) { ElMessage.error('属性名称不能为空'); return }
      }
      for (const instance of currentEntity.value.instances) {
        if (!instance.trim()) { ElMessage.error('实例名称不能为空'); return }
      }

      const session = driver.session({ database: database_name })
      try {
        if (isEditingEntity.value) {
          await session.run(
            `MATCH (e:Entity {id: $id}) SET e.name = $name, e.label = $label, e.definition = $definition`,
            { id: currentEntity.value.id, name: currentEntity.value.name, label: currentEntity.value.label, definition: currentEntity.value.definition }
          )
          await session.run(`MATCH (e:Entity {id: $id})-[r:HAS_PROPERTY]->(p:Property) DELETE r, p`, { id: currentEntity.value.id })
          for (const property of currentEntity.value.properties) {
            await session.run(`MATCH (e:Entity {id: $entityId}) CREATE (p:Property {id: randomUUID(), name: $name}), (e)-[:HAS_PROPERTY]->(p)`, { entityId: currentEntity.value.id, name: property })
          }
          await session.run(`MATCH (e:Entity {id: $id})-[r:HAS_INSTANCE]->(i:Instance) DELETE r, i`, { id: currentEntity.value.id })
          for (const instance of currentEntity.value.instances) {
            await session.run(`MATCH (e:Entity {id: $entityId}) CREATE (i:Instance {id: randomUUID(), name: $name}), (e)-[:HAS_INSTANCE]->(i)`, { entityId: currentEntity.value.id, name: instance })
          }
          await session.run(`MATCH (e:Entity {id: $id})-[:BELONGS_TO]->(o:Ontology) SET o.updateTime = toString(datetime())`, { id: currentEntity.value.id })
          ElMessage.success('实体更新成功')
        } else {
          const result = await session.run(
            `MATCH (o:Ontology {id: $ontologyId}) CREATE (e:Entity {id: randomUUID(), name: $name, label: $label, definition: $definition})-[:BELONGS_TO]->(o) RETURN e.id as id`,
            { ontologyId: editingOntology.value.id, name: currentEntity.value.name, label: currentEntity.value.label, definition: currentEntity.value.definition }
          )
          const entityId = result.records[0].get('id')
          for (const property of currentEntity.value.properties) {
            await session.run(`MATCH (e:Entity {id: $entityId}) CREATE (p:Property {id: randomUUID(), name: $name}), (e)-[:HAS_PROPERTY]->(p)`, { entityId: entityId, name: property })
          }
          for (const instance of currentEntity.value.instances) {
            await session.run(`MATCH (e:Entity {id: $entityId}) CREATE (i:Instance {id: randomUUID(), name: $name}), (e)-[:HAS_INSTANCE]->(i)`, { entityId: entityId, name: instance })
          }
          await session.run(`MATCH (o:Ontology {id: $ontologyId}) SET o.updateTime = toString(datetime())`, { ontologyId: editingOntology.value.id })
          ElMessage.success('实体创建成功')
        }
        await handleEdit(editingOntology.value)
        entityDialogVisible.value = false
      } catch (error) {
        console.error('Error saving entity:', error)
        ElMessage.error('保存实体失败: ' + error.message)
      } finally {
        session.close()
      }
    }

    const deleteEntity = async (entity) => {
      const session = driver.session({ database: database_name })
      try {
        await session.run(`MATCH (e:Entity {id: $id}) DETACH DELETE e`, { id: entity.id })
        ElMessage.success('实体及所有关联关系删除成功')
        await handleEdit(editingOntology.value)
      } catch (error) {
        console.error('Error deleting entity:', error)
        ElMessage.error('删除实体失败: ' + error.message)
      } finally {
        session.close()
      }
    }

    const relationDialogVisible = ref(false)
    const isEditingRelation = ref(false)
    const currentRelation = ref({ name: '', label: '', from: '', to: '', definition: '' })

    const saveRelation = async () => {
      if (!currentRelation.value.name.trim()) { ElMessage.error('关系名称不能为空'); return }
      if (!currentRelation.value.from) { ElMessage.error('请选择头实体'); return }
      if (!currentRelation.value.to) { ElMessage.error('请选择尾实体'); return }
      const session = driver.session({ database: database_name })
      try {
        if (isEditingRelation.value) {
          await session.run(
            `MATCH ()-[r:RELATION {id: $id}]->() SET r.name = $name, r.label = $label, r.definition = $definition`,
            { id: currentRelation.value.id, name: currentRelation.value.name, label: currentRelation.value.label, definition: currentRelation.value.definition }
          )
          ElMessage.success('关系更新成功')
        } else {
          await session.run(
            `MATCH (from:Entity {name: $from}), (to:Entity {name: $to})
             WHERE (from)-[:BELONGS_TO]->(:Ontology {id: $ontologyId}) AND (to)-[:BELONGS_TO]->(:Ontology {id: $ontologyId})
             CREATE (from)-[r:RELATION {id: apoc.create.uuid(), name: $name, label: $label, definition: $definition}]->(to)`,
            {
              ontologyId: editingOntology.value.id, name: currentRelation.value.name, label: currentRelation.value.label,
              definition: currentRelation.value.definition, from: currentRelation.value.from, to: currentRelation.value.to
            }
          )
          ElMessage.success('关系创建成功')
        }
        await handleEdit(editingOntology.value)
        relationDialogVisible.value = false
      } catch (error) {
        console.error('Error saving relation:', error)
        ElMessage.error('保存关系失败: ' + error.message)
      } finally {
        session.close()
      }
    }

    const deleteRelation = async (relation) => {
      const session = driver.session({ database: database_name })
      try {
        await session.run(`MATCH ()-[r:RELATION {id: $id}]->() DELETE r`, { id: relation.id })
        ElMessage.success('关系删除成功')
        await handleEdit(editingOntology.value)
      } catch (error) {
        console.error('Error deleting relation:', error)
        ElMessage.error('删除关系失败')
      } finally {
        session.close()
      }
    }

    onMounted(() => { loadOntologies() })

    const canvas = ref(null)
    let svg = null

    const showCreateDialog = () => {
      newOntology.value = { name: '', description: '' }
      createDialogVisible.value = true
    }

    const showCreateEntityDialog = () => {
      isEditingEntity.value = false
      currentEntity.value = { name: '', label: '', definition: '', properties: ['实体名'], instances: [] }
      entityDialogVisible.value = true
    }

    const editEntity = (entity) => {
      isEditingEntity.value = true
      currentEntity.value = JSON.parse(JSON.stringify(entity))
      if (!currentEntity.value.properties.includes('实体名')) {
        currentEntity.value.properties.unshift('实体名')
      }
      entityDialogVisible.value = true
    }

    const addProperty = () => { currentEntity.value.properties.push('') }
    const removeProperty = (index) => {
      if (index === 0) { ElMessage.warning('默认属性"实体名"不可删除'); return }
      currentEntity.value.properties.splice(index, 1)
    }

    const showCreateRelationDialog = () => {
      isEditingRelation.value = false
      currentRelation.value = { name: '', label: '', from: '', to: '', definition: '' }
      relationDialogVisible.value = true
    }

    const editRelation = (relation) => {
      isEditingRelation.value = true
      currentRelation.value = JSON.parse(JSON.stringify(relation))
      relationDialogVisible.value = true
    }

    const initCanvas = () => {
      if (!canvas.value) return
      d3.select('#ontology-canvas').selectAll('*').remove()
      const width = canvas.value.clientWidth
      const height = canvas.value.clientHeight
      const zoom = d3.zoom().scaleExtent([0.1, 5]).on('zoom', (event) => { svg.attr('transform', event.transform) })
      const container = d3.select('#ontology-canvas').append('svg').attr('width', width).attr('height', height).call(zoom)
      svg = container.append('g')
      const nodes = []
      const links = []
      const nodeMap = new Map()

      entities.value.forEach(entity => {
        const node = { id: entity.id, name: entity.name, type: 'entity' }
        nodes.push(node)
        nodeMap.set(entity.name, node)
        entity.properties.forEach((property, index) => {
          const propId = `${entity.id}-prop-${index}`
          const propNode = { id: propId, name: property, type: 'property' }
          nodes.push(propNode)
          links.push({ source: node, target: propNode, type: 'property' })
        })
        entity.instances.forEach((instance, index) => {
          const instanceId = `${entity.id}-inst-${index}`
          const instNode = { id: instanceId, name: instance, type: 'instance' }
          nodes.push(instNode)
          links.push({ source: node, target: instNode, type: 'instance' })
        })
      })

      relations.value.forEach(relation => {
        const sourceNode = nodeMap.get(relation.from)
        const targetNode = nodeMap.get(relation.to)
        if (sourceNode && targetNode) {
          links.push({ source: sourceNode, target: targetNode, name: relation.name || relation.label || '', type: 'relation' })
        }
      })

      svg.append('defs').selectAll('marker').data(['relation']).enter().append('marker')
        .attr('id', d => `arrow-${d}`).attr('viewBox', '0 -5 10 10').attr('refX', 25).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6).attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#999')

      const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(150))
        .force('charge', d3.forceManyBody().strength(-500))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(40))

      const link = svg.append('g').selectAll('line').data(links).enter().append('line')
        .attr('stroke', d => d.type === 'relation' ? '#666' : '#ccc').attr('stroke-width', 2)
        .attr('marker-end', d => d.type === 'relation' ? 'url(#arrow-relation)' : null)

      const linkTextBg = svg.append('g').selectAll('rect').data(links.filter(d => d.name && d.type === 'relation')).enter().append('rect')
        .attr('rx', 4).attr('ry', 4).attr('fill', 'white').attr('stroke', '#ccc')

      const linkText = svg.append('g').selectAll('text').data(links.filter(d => d.name && d.type === 'relation')).enter().append('text')
        .attr('font-size', 12).attr('fill', '#333').text(d => d.name).attr('text-anchor', 'middle')

      const node = svg.append('g').selectAll('g').data(nodes).enter().append('g')
        .call(d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended))

      node.append('circle').attr('r', d => d.type === 'entity' ? 20 : 16).attr('fill', d => {
        switch(d.type) {
          case 'entity': return '#69b3a2'; case 'property': return '#ff9f43';
          case 'instance': return '#54a0ff'; default: return '#ddd'
        }
      })

      node.append('text').attr('dx', d => d.type === 'entity' ? 25 : 20).attr('dy', '.35em').text(d => d.name)
        .style('font-size', d => d.type === 'entity' ? '14px' : '12px')
        .style('font-weight', d => d.type === 'entity' ? 'bold' : 'normal')
        .attr('paint-order', 'stroke').attr('stroke', 'white').attr('stroke-width', '3px').attr('stroke-linecap', 'round');


      function ticked() {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y)
        node.attr('transform', d => `translate(${d.x},${d.y})`)
        linkText.attr('x', d => (d.source.x + d.target.x) / 2).attr('y', d => (d.source.y + d.target.y) / 2)
        linkTextBg.each(function(d) {
          const textElement = linkText.filter(td => td === d).node();
          if (textElement) {
            const bbox = textElement.getBBox()
            d3.select(this).attr('x', bbox.x - 2).attr('y', bbox.y - 2)
              .attr('width', bbox.width + 4).attr('height', bbox.height + 4)
          }
        })
      }

      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
      }
      function dragged(event, d) { d.fx = event.x; d.fy = event.y }
      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null; d.fy = null
      }
      simulation.on('tick', ticked)
    }

    watch(mode, (newVal) => {
      if (newVal === 'canvas') {
        nextTick(() => { initCanvas() })
      }
    })

    return {
      ontologyList, createDialogVisible, newOntology, editDialogVisible, editingOntology, mode, entities, relations,
      entityDialogVisible, isEditingEntity, currentEntity, relationDialogVisible, isEditingRelation, currentRelation, canvas,
      showCreateDialog, createOntology, handleEdit, handleDelete, showCreateEntityDialog, editEntity, deleteEntity, addProperty,
      removeProperty, saveEntity, showCreateRelationDialog, editRelation, deleteRelation, saveRelation, addInstance,
      removeInstance, toggleEdit, saveEdit, Plus, Edit, Delete, Grid, Picture,
    }
  }
}
</script>

<style scoped>
.ontology-container {
  padding: 24px;
  background-color: #f4f6f8;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
  height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px 28px;
  background: linear-gradient(135deg, #5dade2 0%, #2980b9 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(56, 249, 215, 0.2);
}
.header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
}

.box-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-bottom: 20px;
}
.ontology-name {
  font-weight: 500;
  color: #303133;
}
.ontology-description {
  color: #606266;
  font-size: 14px;
}

:deep(.el-table th) {
  background-color: #fafbfe !important;
  color: #303133;
  font-weight: 600;
}
:deep(.el-table tr:hover > td) {
  background-color: #f0faff !important;
}

/* Edit Mode Styles */
.edit-container {
  height: calc(100vh - 55px); /* Fullscreen dialog has some padding */
  display: flex;
  flex-direction: column;
}

.mode-switch {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.table-mode {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.canvas-mode {
  flex: 1;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
  background-color: #fff;
  background-image:
    linear-gradient(rgba(0, 0, 0, .08) .1em, transparent .1em),
    linear-gradient(90deg, rgba(0, 0, 0, .08) .1em, transparent .1em);
  background-size: 1.5em 1.5em;
}

#ontology-canvas {
  width: 100%;
  height: 100%;
}

/* Dialog Form Item Styles */
.property-item,
.instance-item {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  align-items: center;
}
.add-button {
  width: auto;
  margin-top: 5px;
}

</style>