const servicesContent = {
    1: {
    title: "Gestión de Productos",
    text: "Ayudamos a planificar, desarrollar, lanzar y gestionar sus productos a lo largo de todo su ciclo de vida.",
    bgColor: "#007acc"
    },
    2: {
    title: "Control de Ejecutivos",
    text: "Revisamos el estado de las ventas y el rendimiento de los ejecutivos para optimizar las estrategias.",
    bgColor: "#005fa3"
    },
    3: {
    title: "Reportes de Ventas",
    text: "Realizamos reportes detallados sobre el rendimiento de ventas para tomar decisiones informadas.",
    bgColor: "#004a80"
    },
    4: {
    title: "Asignación de Metas",
    text: "Luego de obtener los reportes, asignamos metas a los ejecutivos para mejorar el rendimiento.",
    bgColor: "#006bb3"
    },
    5: {
    title: "Soporte Personalizado",
    text: "Si el cliente lo amerita ofrecemos soporte personalizado para resolver problemas técnicos.",
    bgColor: "#0080d6"
    },
    6: {
    title: "Historial y Backups",
    text: "Ofrecemos un historial de cambios y backups para asegurar la integridad de los datos.",
    bgColor: "#005fa3"
    }
};

const leftBox = document.getElementById("leftBox");
const servicesList = document.getElementById("servicesList");
const items = servicesList.querySelectorAll("li");

items.forEach(item => {
    item.addEventListener("click", () => {
    items.forEach(i => i.classList.remove("active"));
    item.classList.add("active");
    
    const id = item.getAttribute("data-id");
    const content = servicesContent[id];
    
    leftBox.innerHTML = `
        <h2>${content.title}</h2>
        <p>${content.text}</p>
    `;
    leftBox.style.backgroundColor = content.bgColor;
    });
});
