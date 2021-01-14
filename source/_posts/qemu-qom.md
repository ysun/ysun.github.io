---
title: 利用QOM(Qemu Object Model)创建虚拟设备
donate: true
date: 2018-12-26 09:42:27
categories: QEMU
tags: [QEMU, QOM]
---

## 什么是QOM
QOM(Qemu Object Model)是QEMU最新的设备模型，将所有的模拟设备整合成了一种单根结点(系统总线)的树状形式，并具有热插拔功能。后来可能由于Device和Bus之间的复杂关系，又开发了QOM。
QOM是QEMU在C的基础上自己实现的一套面向对象机制，负责将device、bus等设备都抽象成为对象。
## QOM 的初始化
对象的初始化分为四步：
+ 将 TypeInfo 注册 TypeImpl
+ 实例化 ObjectClass
+ 实例化 Object
+ 添加 Property

根据QEMU的wiki ，QOM没有构造和析构的概念。但矛盾的是根据代码，TypeInfo 中定义的 class_init 和 instance_init 无论从名字还是实现上都做了对象的初始化工作，比如设置对象成员的值。但为什么说它们最多只能算是初始化函数呢？
`Everything in QOM is a device`
根据实现，经过 class_init 和 instance_init 产生设备对应Object后，这个Object是不能直接使用的。其真正初始化逻辑的大头都放在 realize 中做，比如创建对应的memory region，挂载到对应bus上等等。只有在 realize 后，设备才算真正构造完成，可以拿来用了。因此QEMU认为，类似构造和析构的是realize和unrealize。而在设备的生命周期中，可以被realize和unrealize多次。
为了保持习惯，本文会依然将 class_init 和 instance_init 当做构造函数，称前者为类构造函数，后者为类实例构造函数。
## 使用QOM添加设备源码分析
下面我们就利用一个真实的案例，讲解一下利用QOM添加设备的具体实现步骤
### TypeInfo => ModuleEntry

设备相关代码的入口就是这里了, TypeInfo 定义了一种类型，并且使用函数type_register_static注册：

```
static const TypeInfo caffee_agent_info = {
    .name          = "caffee-agent",
    .parent        = TYPE_ISA_DEVICE,
    .class_init    = caffee_agent_class_init,
    .instance_size = sizeof(CaffeeAgentState),
    .instance_init = caffee_agent_initfn,
};
                                             
static void caffee_agent_register_types (void)
{
    type_register_static (&caffee_agent_info);
}

type_init(cafe_agent_register_types)
```
包含 类型的名称(name)、父类名称(parent)、Object实例的大小(instance_size)、是否抽象类(abstract)、初始化函数(class_init)。
代码底部有 type_init ，由 C run-time(CRT)负责执行：
<!--
`type_init(kvm_type_init) => module_init(function, MODULE_INIT_QOM) => register_module_init(function, type)`
-->

``` flow
op1=>operation: type_init(kvm_type_init)
op2=>operation: module_init(function, MODULE_INIT_QOM)
op3=>operation: register_module_init(function, type)
op1(right)->op2(right)->op3
```

```
void register_module_init(void (*fn)(void), module_init_type type)
{
    ModuleEntry *e;
    ModuleTypeList *l;

    e = g_malloc0(sizeof(*e));
    e->init = fn;
    e->type = type;

    l = find_type(type);

    QTAILQ_INSERT_TAIL(l, e, node);
}
```
创建了 type 为 MODULE_INIT_QOM ，init为 kvm_type_init 的 ModuleEntry ，并加入到 MODULE_INIT_QOM 的 ModuleTypeList 中。

### ModuleEntry => TypeImpl

在 main.c(vl.c) 的一开始执行了 module_call_init(MODULE_INIT_QOM) ，它从 init_type_list 中取出对应的 ModuleTypeList ，然后对里面的 ModuleEntry 成员都调用 init 函数。
对于上文提到的 ModuleEntry ，调用的是：
<!---
`kvm_type_init => type_register_static(&kvm_accel_type) => type_register => type_register_internal`
-->

```flow
op1=>operation: kvm_type_init
op2=>operation: type_register_static(&kvm_accel_type)
op3=>operation: type_register
op4=>operation: type_register_internal

op1(right)->op2(right)->op3(right)->op4
```

```
static TypeImpl *type_register_internal(const TypeInfo *info)
{
    TypeImpl *ti;
    ti = type_new(info);

    type_table_add(ti);
    return ti;
}
```
它根据 kvm_accel_type(TypeInfo) 创建一个名为TYPE_KVM_ACCEL的 TypeImpl 类型的结构。
同时将该 TypeImpl 注册到全局 type_table 中，key为类型名称，即 TYPE_KVM_ACCEL

### ObjectClass
```
struct ObjectClass
{
    /*< private >*/
    Type type;              // 用typedef定义的 TypeImpl 指针
    GSList *interfaces;

    const char *object_cast_cache[OBJECT_CLASS_CAST_CACHE];
    const char *class_cast_cache[OBJECT_CLASS_CAST_CACHE];

    ObjectUnparent *unparent;

    GHashTable *properties;
};
```
ObjectClass 属于类对象，它是所有类对象的基类。

#### TypeImpl => ObjectClass
有两种路径，一种是主动地调用：
<!---
`object_class_get_list => object_class_foreach => g_hash_table_foreach(object_class_foreach_tramp) => object_class_foreach_tramp => type_initialize`
-->
``` flow
op1=>operation: object_class_get_list
op2=>operation: object_class_foreach
op3=>operation: g_hash_table_foreach(object_class_foreach_tramp)
op4=>operation: object_class_foreach_tramp
op5=>operation: type_initialize

op1(right)->op2(right)->op3(right)->op4(right)->op5
```
比如 object_class_get_list(TYPE_DEVICE, false) 创建 TYPE_DEVICE 类型的 ObjectClass
该过程用到glic的函数 g_hash_table_foreach ，见 https://developer.gnome.org/glib/stable/glib-Hash-Tables.html#g-hash-table-foreach
另一种是被动调用，如:
+ object_class_by_name
+ object_class_get_parent
+ object_new_with_type
+ object_initialize_with_type

在获取 class、class的parent、创建type的object、初始化TypeImpl的object时，调用 type_initialize
```
type_initialize
=> 如果 TypeImpl 已创建(class成员有值)，返回
=> ti->class = g_malloc0(ti->class_size)                    根据class_size分配内存空间
=> type_get_parent(ti)                                      获取父类的TypeImpl
=> memcpy(ti->class, parent->class, parent->class_size)     将parent的class拷贝到自己class的最前面
=> ti->class->properties = g_hash_table_new_full            创建存放property的hash table
=> type_initialize_interface                                初始化class的接口，包括父类和自己的
=> ti->class->type = ti                                     设置class的type为对应TypeImpl
=> parent->class_base_init                                  如果parent定义了 class_base_init ，调用之
=> ti->class_init(ti->class, ti->class_data)                调用class的 class_init
```
对于 kvm_accel_type 这个 TypeInfo 的 TypeImpl ，调用的class_init是 kvm_accel_class_init ，它将传入的 ObjectClass 强转为子类 AccelClass ，设置 init_machine 成员为 kvm_init
这里的class是该类型的类实例，它的基类是 ObjectClass 。

#### 继承
从创建流程可以看出，在创建类对象时，会调用 type_initialize ，其会递归地对 TypeImpl 中的 parent 成员(TypeImpl)递归调用 type_initialize ，然后将创建出来的相应 ObjectClass 拷贝到自己class的最前面。
类对象的第一个成员是 parent_class ，由于父类对象会拷到子类对象的最前面，因此可以认为其指向父类的对象，如此构成链状的继承链，最终指向基类对象 ObjectClass
比如 kvm_accel_type 对应的类对象，该类对象作为叶子类型并没有定义，但其父类 AccelClass 在代码中有定义，其的第一个成员为 ObjectClass ，表示其继承自 ObjectClass 。为了能表示该叶子类型继承 AccelClass ，它修改了 AccelClass的一些对象成员，这样在某种程度上表示了继承关系。比如修改了函数指针成员的指向，相当于实现了虚函数。
又如： `register_info 对应的类对象 => PCIDeviceClass => DeviceClass => ObjectClass` 构成继承链，最前端的叶子类型通过修改 PCIDeviceClass 成员进行定义。
#### 强制类型转换
将一个父类的指针转换为子类的指针是不安全的，为了实现这种转换，各类需要提供强制类型转换的宏，如：
```
#define ACCEL_CLASS(klass) \
    OBJECT_CLASS_CHECK(AccelClass, (klass), TYPE_ACCEL)

#define OBJECT_CLASS_CHECK(class_type, class, name) \
    ((class_type *)object_class_dynamic_cast_assert(OBJECT_CLASS(class), (name), \
                                               __FILE__, __LINE__, __func__))
```
如果类对象指针的name和目标子类的name一致，或类对象指针是目标子类的祖先，则执行转换，否则 abort
反过来，从子类指针转换为父类指针是安全的，因为类的第一项就指向父类，访问时不会存在越界等问题。 

### Object
Object 属于类实例对象，它是所有类实例对象的基类。
```
struct Object
{
    /*< private >*/
    ObjectClass *class;             // 指向类对象
    ObjectFree *free;
    GHashTable *properties;         // 维护属性的哈希表
    uint32_t ref;                   // 引用计数
    Object *parent;                 // 指向父类实例对象，实现继承
};
```
可以看到其第一个成员指向类对象，同时维护有区别于类属性的类实例属性。
#### 创建流程
就流程而言，在C runtime 根据 TypeInfo 创建了 TypeImpl 后，此后主要根据 TypeImpl 创建 ObjectClass 和 Object
以 TypeInfo(kvm_accel_type) 为例，其创建的 TypeImpl 在以下流程发挥作用：
```
main => configure_accelerator => accel_init_machine(acc, ms)
=> ObjectClass *oc = OBJECT_CLASS(acc)                                  将AccelClass指针转换成父类(ObjectClass)指针
=> object_class_get_name                                                获取 ObjectClass->TypeImpl 的类名，如 kvm-accel
=> ACCEL(object_new(cname))                                             利用名称创建 AccelState 对象
=> acc->init_machine(ms)                                                初始化machine，实际上是调用 kvm_init

object_new
=> type_get_by_name(typename)                                           根据类名查type_table获取 TypeImpl
=> object_new_with_type => type_initialize                              创建 TypeImpl 对应的类对象，设置到对应 TypeImpl->class 中
                        => g_malloc(type->instance_size)                分配类实例对象的内存
                        => object_initialize_with_type                  创建类实例对象
                            => type_initialize  会再次尝试实例化类对象
                            => obj->class = type->class                 设置类实例对象的类对象为 TypeImpl->class
                            => obj->properties = g_hash_table_new_full  创建存放类实例对象property的hash table
                            => object_init_with_type => object_init_with_type   如果 TypeImpl 有父类，递归调用object_init_with_type
                                                     => ti->instance_init(obj)  如果定义了类实例的构造函数，调用之
```
#### 继承
定义上的继承主要指类的继承，既然类对象已经通过包含的方式实现了继承，那么类实例对象就可以通过调用自己的class成员调用父类的函数，访问父类的class property。
但在QEMU实现的这套面向对象模型中，类实例对象也拥有自己的构造函数，因此根据继承关系，需要对父类实例对象的构造函数进行调用。
从创建流程可以看出，在创建类实例对象时，会调用 object_init_with_type ，其会递归地对 TypeImpl 中的 parent 成员递归调用 object_init_with_type ，从而让所有父类的 instance_init 都得到调用，在调用时传入的是当前对象的地址，相当于在当前对象上对父类实例对象进行构造。
同理，类实例对象的第一个成员是 parent_obj ，指向父类的实例对象，如此构成链状的继承链，最终指向基类实例对象 Object
如： kvm_accel_type的类实例Object => AccelState => Object
又如： register_info的类实例Object => PCIDevice => DeviceState => Object
#### 强制类型转换
同理，将一个父类实例的指针转换为子类实例指针是不安全的。为了实现这种转换，各类需要提供强制类型转换的宏，如：
```
#define ACCEL(obj) \
    OBJECT_CHECK(AccelState, (obj), TYPE_ACCEL)

#define OBJECT_CHECK(type, obj, name) \
    ((type *)object_dynamic_cast_assert(OBJECT(obj), (name), \
                                        __FILE__, __LINE__, __func__))
```
如果类实例对象指针的name和目标子类实例的name一致，或类实例对象指针是目标子类的祖先，则执行转换，否则 abort。
反过来，从子类实例指针转换为父类实例指针是安全的，因为类实例的第一项就指向父类实例，访问时不会存在越界等问题。
### 属性
属性分为类对象(ObjectClass)属性和类实例对象(Object)属性，存储于 properties 成员中。properties 是一个 GHashTable ，存储了属性名到ObjectProperty的映射。
#### 属性模版
用于创建属性对象 ObjectProperty
```
struct Property {
    const char   *name;
    PropertyInfo *info;
    ptrdiff_t    offset;
    uint8_t      bitnr;
    QType        qtype;
    int64_t      defval;
    int          arrayoffset;
    PropertyInfo *arrayinfo;
    int          arrayfieldsize;
};
```
#### 属性对象
属性对象包含属性名称、类型、描述，类型对应的属性结构，以及相应访问函数。
```
typedef struct ObjectProperty
{
    gchar *name;
    gchar *type;
    gchar *description;
    ObjectPropertyAccessor *get;
    ObjectPropertyAccessor *set;
    ObjectPropertyResolve *resolve;
    ObjectPropertyRelease *release;
    void *opaque;
} ObjectProperty;
```
如对于bool类型的属性，opaque为 BoolProperty ，set为 property_set_bool ，get为 property_get_bool 。
```
typedef struct BoolProperty
{
    bool (*get)(Object *, Error **);
    void (*set)(Object *, bool, Error **);
} BoolProperty;
```
用于保存用户传入的 getter 和 setter 。
#### getter / setter (callback hook)
定义了在设置/读取属性时触发的函数。
比如 device 类型的 instance_init 即 device_initfn 中，定义了 realized 属性：
```
object_property_add_bool(obj, "realized", device_get_realized, device_set_realized, NULL)

```
则 getter 为 device_get_realized ， setter 为 device_set_realized
#### 静态属性
凡是在代码中就已经定义好名称和类型的属性，都是静态属性。包括在初始化过程中添加 和 props 。
##### 初始化过程中添加
比如对于 TypeInfo x86_cpu_type_info ，类实例初始化函数 x86_cpu_initfn 定义好了属性：
```
object_property_add(obj, "family", "int",
                    x86_cpuid_version_get_family,
                    x86_cpuid_version_set_family, NULL, NULL, NULL);

object_property_add_alias(obj, "kvm_steal_time", obj, "kvm-steal-time", &error_abort);
```
该属性会直接加到类实例对象的properties中。
##### props
一些类对象会在 class_init 中设置 props 成员，比如 TypeInfo host_x86_cpu_type_info 在 host_x86_cpu_class_init 设置为 host_x86_cpu_properties：
```
static Property host_x86_cpu_properties[] = {
    DEFINE_PROP_BOOL("migratable", X86CPU, migratable, true),
    DEFINE_PROP_BOOL("host-cache-info", X86CPU, cache_info_passthrough, false),
    DEFINE_PROP_END_OF_LIST()
};

#define DEFINE_PROP_BOOL(_name, _state, _field, _defval) {       \
        .name      = (_name),                                    \
        .info      = &(qdev_prop_bool),                          \
        .offset    = offsetof(_state, _field)                    \
            + type_check(bool, typeof_field(_state, _field)),    \
        .qtype     = QTYPE_QBOOL,                                \
        .defval    = (bool)_defval,                              \
        }

// 闭包
PropertyInfo qdev_prop_bool = {
    .name  = "bool",
    .get   = get_bool,
    .set   = set_bool,
};
```
而类实例 X86CPU 中定义了这些属性：
```
struct X86CPU {
    bool migratable;
    ...
    bool cache_info_passthrough;
    ...
};
```
于是 X86CPU.migratable 和 X86CPU.cache_info_passthrough 两个成员被定义成属性。

在父类 device_type_info 的类实例初始化函数 device_initfn 中，对所有的props，有：
```
    do {
        for (prop = DEVICE_CLASS(class)->props; prop && prop->name; prop++) {
            qdev_property_add_legacy(dev, prop, &error_abort);
            qdev_property_add_static(dev, prop, &error_abort);
        }
        class = object_class_get_parent(class);
    } while (class != object_class_by_name(TYPE_DEVICE));
```
而 qdev_property_add_static ：
<pre>
=> object_property_add(obj, prop->name, prop->info->name, prop->info->get, prop->info->set, prop->info->release, prop, &local_err)
    根据Property中的数据，创建ObjectProperty，并将其加到类实例对象的 properties 中
    关键是将闭包中的get和set取出，作为ObjectProperty的get和set
=> object_property_set_description     设置属性的描述字符串
=> 设置属性的默认值
</pre>
##### 查看
可通过命令查看设备的静态属性，参数为设备 TypeInfo 的 name：
```
/home/binss/work/qemu/qemu-2.8.1.1/x86_64-softmmu/qemu-system-x86_64 -device Broadwell-x86_64-cpu,?
```
但是， x86_64-cpu 抽象设备无法打。 host-x86_64-cpu 无法列出。
#### 动态属性
指在运行时动态进行添加的属性。比如用户通过参数传入了一个设备，需要作为属性和其它设备关联起来。
典型的动态属性就是 child<> 和 link<> (因为其类型就是这样构造的，后文简称child和link) 。
##### child
child实现了composition关系，表示一个设备(parent)创建了另外一个设备(child)，parent掌控child的生命周期，负责向其发送事件。一个device只能有一个parent，但能有多个child。这样就构成一棵组合树。
通过 object_property_add_child 添加child：
```
=> object_property_add            将 child 作为 obj 的属性，属性名name，类型为 "child<child的类名>"，同时getter为object_get_child_property，没有setter
=> child->parent = obj
```
例如 x86_cpu_realizefn => x86_cpu_apic_create => object_property_add_child(OBJECT(cpu), "lapic", OBJECT(cpu->apic_state), &error_abort) 将创建 APICCommonState ，并设置为 X86CPU 的child。
可以在qemu hmp查询到：
```
(qemu) info qom-tree
/machine (pc-q35-2.8-machine)
  /unattached (container)
    /device[0] (host-x86_64-cpu)
```
##### link
link实现了backlink关系，表示一个设备引用了另外一个设备，是一种松散的联系。两个设备之间能有多个link关系，可以进行修改。它完善了组合树，使其构成构成了一幅有向图。
通过 object_property_add_link 添加link：
```
=> 创建 LinkProperty ，填充目标(child)的信息
=> object_property_add            将 LinkProperty 作为 obj 的属性，属性名name，类型为 "link<child的类名>"，同时getter为 object_get_link_property 。如果传入了check函数，则需要回调，设置setter为 object_set_link_property
```
例如 q35 有以下link：
```
static void q35_host_initfn(Object *obj)
{
    object_property_add_link(obj, MCH_HOST_PROP_RAM_MEM, TYPE_MEMORY_REGION,
                             (Object **) &s->mch.ram_memory,
                             qdev_prop_allow_set_link_before_realize, 0, NULL);

    object_property_add_link(obj, MCH_HOST_PROP_PCI_MEM, TYPE_MEMORY_REGION,
                             (Object **) &s->mch.pci_address_space,
                             qdev_prop_allow_set_link_before_realize, 0, NULL);

    object_property_add_link(obj, MCH_HOST_PROP_SYSTEM_MEM, TYPE_MEMORY_REGION,
                             (Object **) &s->mch.system_memory,
                             qdev_prop_allow_set_link_before_realize, 0, NULL);

    object_property_add_link(obj, MCH_HOST_PROP_IO_MEM, TYPE_MEMORY_REGION,
                             (Object **) &s->mch.address_space_io,
                             qdev_prop_allow_set_link_before_realize, 0, NULL);
}
```
将 Q35PCIHost 和 ram_memory / pci_address_space / system_memory / address_space_io 链接起来。
#### API
根据前面所述，属性有两种定义方式，一种是通过 `DEFINE_PROP_*` 定义，另一种是通过 `object_property_add_<type>` 进行定义。根据不同的定义方式，set会不同，设置值的方式也有所不同。
##### `object_property_set_<type>`
用于设置某个属性的值。比如 object_property_set_bool ：
```
=> qbool_from_bool                                              将要设置的值包装成相应的 QObject ，这里是QBool
=> object_property_set_qobject
    => qobject_input_visitor_new                                将传入的QObject包装成Visitor，其中含各类型的处理函数
    => object_property_set => object_property_find              从props的hash table中找到对应的 ObjectProperty
                           => prop->set
```
对于 DEFINE_PROP_BOOL 创建的属性来说，其闭包为qdev_prop_bool，因此在初始化时 set 被设置为 set_bool
```
set_bool
=> qdev_get_prop_ptr                                                                       将设备指针加上属性值在其中的偏移量，得到属性值的地址
=> visit_type_bool => v->type_bool (qobject_input_type_bool) => qobject_input_get_object   从Visitor中取出QObject
                                                             => qbool_get_bool             从QObject中取出值，设置到属性值的地址
```
对于 object_property_add_bool 创建的属性来说，它在 object_property_add 时设置 set 为 property_set_bool
```
property_set_bool
=> visit_type_bool => v->type_bool (qobject_input_type_bool) => qobject_input_get_object  找到QObject
=> (BoolProperty)prop->set    调用setter
```
比如 device 类型的 instance_init 即 device_initfn 中，定义了 realized 属性：
```
object_property_add_bool(obj, "realized", device_get_realized, device_set_realized, NULL)
```
于是 setter 为 device_set_realized
```
=> dc->realize                                      调用realize函数，其在 class_init 中定义
=> dev->realized = value                            设置类实例对象的成员
```
一句话总结，前者的属性值的设置由 type_bool 负责设置，而后者由 setter 负责设置。
##### `object_property_get_<type>`
用于读取某个属性的值。比如 object_property_get_bool ：
```
=> object_property_get_qobject
    => 创建空的QObject指针
    => qobject_output_visitor_new                                                           将传入的QObject包装成Visitor，其中含各类型的处理函数
    => object_property_get => object_property_find                                          从props的hash table中找到对应的 ObjectProperty
                           => prop->get                                                     调用get函数，设置QObject
=> qobject_to_qbool                                                                         将QObject转成QBool
=> qbool_get_bool                                                                           从QBool中取出值，返回
```
对于 DEFINE_PROP_BOOL 创建的属性来说，其闭包为qdev_prop_bool，因此在初始化时 get 被设置为 get_bool
```
get_bool
=> qdev_get_prop_ptr(dev, prop)                                                             将设备指针加上属性值在其中的偏移量，得到属性值的地址
=> visit_type_bool => v->type_bool (qobject_output_type_bool) => qobject_input_get_object   将属性值包装成QObject
```
对于 object_property_add_bool 创建的属性来说，它在 object_property_add 时设置 get 为 property_get_bool ：
```
property_get_bool
=> prop->get                                                                                调用getter，得到属性值
=> visit_type_bool => v->type_bool (qobject_output_type_bool) => qobject_input_get_object   将属性值包装成QObject
```
个人的理解是，set 和 get 都需要通过 QObject 和 Visitor 两层包装。前者把要设置属性值包装成QObject再到Visitor，然后再取出设置到相应地址。后者根据属性值地址将属性值包装成QObject，设置为Visitor中QObject指针指向，然后再从QObject中取出值。
##### object_property_parse
在用一个string设置不知道类型的属性的值时，使用 object_property_parse：
```
void object_property_parse(Object *obj, const char *string,
                           const char *name, Error **errp)
{
    Visitor *v = string_input_visitor_new(string);
    object_property_set(obj, v, name, errp);
    visit_free(v);
}
```
它会创建一个 Visitor 并将值设置到里面，这里定义了string转其他类型属性的函数：
```
    v->visitor.type = VISITOR_INPUT;
    v->visitor.type_int64 = parse_type_int64;
    v->visitor.type_uint64 = parse_type_uint64;
    v->visitor.type_size = parse_type_size;
    v->visitor.type_bool = parse_type_bool;
    v->visitor.type_str = parse_type_str;
    v->visitor.type_number = parse_type_number;
```
### 总结
如此一来，根据 TypeInfo 创建了 TypeImpl ，然后根据 TypeImpl 创建了对应的 ObjectClass ，再根据 TypeImpl 创建了对应的 Object ， ObjectClass 和 Object 都有自己的 Property，关系如下：
```
	                   TypeImpl
                    class      ->  ObjectClass(AccelClass)    Object(AccelState)
                               <-       type            <-         class
    TypeImpl  <-  parent_type    properties(GHashTable)     properties(GHashTable)
```
