(function () {
    const root = document.getElementById("normativeTree");
    const details = document.getElementById("treeDetails");
    const expandBtn = document.getElementById("expandTree");
    const collapseBtn = document.getElementById("collapseTree");

    if (!root || !window.NORMATIVE_TREE) return;

    function renderNode(node, level = 0) {
        const hasChildren = Array.isArray(node.children) && node.children.length > 0;
        const item = document.createElement("div");
        item.className = `tree-node level-${level}`;

        const button = document.createElement("button");
        button.type = "button";
        button.className = `tree-node-button ${node.color || ""}`;
        button.innerHTML = `
            <span class="tree-toggle">${hasChildren ? "▾" : "•"}</span>
            <span class="tree-node-title">${node.number ? node.number + ". " : ""}${node.title}</span>
        `;

        const children = document.createElement("div");
        children.className = "tree-children";

        button.addEventListener("click", () => {
            if (hasChildren) item.classList.toggle("collapsed");
            showDetails(node);
        });

        item.appendChild(button);

        if (hasChildren) {
            node.children.forEach(child => children.appendChild(renderNode(child, level + 1)));
            item.appendChild(children);
        }

        return item;
    }

    function showDetails(node) {
        const example = node.example ? `<p><strong>Пример:</strong> ${node.example}</p>` : "";
        const description = node.description ? `<p>${node.description}</p>` : "";
        const link = node.slug ? `<a class="btn primary" href="/categories/${node.slug}">Открыть категорию</a>` : "";
        details.innerHTML = `
            <span class="eyebrow">Выбранный узел</span>
            <h2>${node.number ? node.number + ". " : ""}${node.title}</h2>
            ${description}
            ${example}
            ${link}
        `;
    }

    function setCollapsed(collapsed) {
        root.querySelectorAll(".tree-node").forEach(node => {
            if (collapsed) node.classList.add("collapsed");
            else node.classList.remove("collapsed");
        });
    }

    window.NORMATIVE_TREE.forEach(node => root.appendChild(renderNode(node)));
    expandBtn?.addEventListener("click", () => setCollapsed(false));
    collapseBtn?.addEventListener("click", () => setCollapsed(true));
})();
